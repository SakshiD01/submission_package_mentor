#!/usr/bin/env python3
"""
Serve UI files + strict inference API for scenario simulation.

Run:
  cd experimenting_ml
  python run_ui_inference_api.py --port 8000

Then open:
  http://localhost:8000/UI/sample%20template%20for%20sim_ml_xai_llm_platform%20(1).html
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zipfile import ZipFile

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
NOLHC_SRC = ROOT.parent / "nolhc_ml" / "src"
for pth in (SRC, NOLHC_SRC):
    if str(pth) not in sys.path:
        sys.path.insert(0, str(pth))

from data import load_xy  # noqa: E402
from models import NEEDS_SCALING  # noqa: E402
from nolhc_input_metadata import (  # noqa: E402
    _bounds_from_expvalues,
    _bounds_from_frame,
    _nolhc_designs_candidates,
    build_input_sliders,
    clip_feature,
    merge_bounds,
)
from scenario_dynamic_params import (  # noqa: E402
    apply_dynamic_overrides,
    apply_semantic_excel,
    build_slider_metadata,
    load_dynamic_tables,
    scenario_level_to_column,
)
from training_columns import (  # noqa: E402
    INPUT_DESCRIPTIONS,
    OUTPUT_COLUMN_ORDER,
    OUTPUT_DESCRIPTIONS,
    TRAINING_COLUMN_ORDER,
    col_to_slug,
    input_unit,
    output_unit,
)


def _safe_filename(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", s)


def _build_simulator_payload(preds: Dict[str, Any]) -> Dict[str, Any]:
    """Map API target names to UI slug keys (matches KPI_META / normalizeInferToSimulatorResult)."""
    out: Dict[str, Any] = {}
    for target, row in preds.items():
        slug = col_to_slug(str(target))
        try:
            y = float(row.get("prediction", 0))
        except (TypeError, ValueError):
            continue
        out[slug] = {
            "value": y,
            "unit": output_unit(str(target)),
            "status": "ok",
            "r2": None,
            "registered_as": str(row.get("model", "")),
            "mae": 0.0,
        }
    return out


def _parse_infer_request_body(req: Dict[str, Any]) -> Dict[str, Any]:
    """Shared POST body fields for /api/infer and /api/predict."""
    family = str(req.get("scenario_family", "routes"))
    level = str(req.get("scenario_level", "baseline"))
    inputs = req.get("inputs") or {}
    focus_target = str(req.get("focus_target", "TT_OB_Agri"))
    include_target_corr = bool(req.get("include_target_corr", False))
    heatmap_targets = req.get("heatmap_targets")
    ht_list: Optional[List[str]] = None
    if isinstance(heatmap_targets, list):
        ht_list = [str(x) for x in heatmap_targets]
    dynamic_sliders = req.get("dynamic_sliders")
    ds_map: Optional[Dict[str, float]] = None
    if isinstance(dynamic_sliders, dict) and dynamic_sliders:
        ds_map = {str(k): float(v) for k, v in dynamic_sliders.items() if v is not None}
    mf = req.get("model_features")
    mf_map: Optional[Dict[str, float]] = None
    if isinstance(mf, dict) and mf:
        mf_map = {str(k): float(v) for k, v in mf.items() if v is not None}
    light = bool(req.get("light", False))
    include_trend = bool(req.get("include_trend", not light))
    mc_samples = int(req.get("mc_samples", 56 if light else 200))
    ot = req.get("output_targets")
    ot_list: Optional[List[str]] = None
    if isinstance(ot, list) and ot:
        ot_list = [str(x) for x in ot]
    return {
        "family": family,
        "level": level,
        "inputs": inputs,
        "focus_target": focus_target,
        "include_target_corr": include_target_corr,
        "heatmap_targets": ht_list,
        "dynamic_sliders": ds_map,
        "model_features": mf_map,
        "include_trend": include_trend,
        "mc_samples": mc_samples,
        "output_targets": ot_list,
    }


def _clip_target_output(target: str, val: float) -> float:
    """Apply physical-domain clipping for outputs."""
    v = float(val)
    if target.startswith(("TT_", "WT_")):
        return max(0.0, v)
    if target.startswith("Uti_"):
        return _clip(v, 0.0, 1.0)
    return v


def _json_sanitize(obj: Any) -> Any:
    """Recursively convert numpy / pandas scalars so json.dumps never raises."""
    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, float):
        return float(obj)
    if isinstance(obj, int):
        return int(obj)
    if isinstance(obj, str):
        return obj
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {str(k): _json_sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_sanitize(v) for v in obj]
    if hasattr(obj, "item"):
        try:
            return _json_sanitize(obj.item())
        except (ValueError, AttributeError, TypeError):
            pass
    return obj


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_selected_models(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            out[str(row["target"])] = str(row["model"])
    return out


def _clip(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))


def _parse_xlsx_scenario_mapping(xlsx_path: Path) -> Dict[str, Dict[str, list[Dict[str, Any]]]]:
    if not xlsx_path.is_file():
        return {}
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    mapping: Dict[str, Dict[str, list[Dict[str, Any]]]] = {
        "routes": {"major_change": [], "change": [], "slight_change": []},
        "border": {"major_change": [], "change": [], "slight_change": []},
    }
    sheet_map = {"Direct Route Scenario": "routes", "Non-Tarriff Barrier": "border"}
    with ZipFile(xlsx_path) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        relmap = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        sst: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            sroot = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in sroot.findall(f"{ns}si"):
                sst.append("".join(t.text or "" for t in si.iter(f"{ns}t")))

        def cval(c: ET.Element) -> Any:
            t = c.attrib.get("t")
            v = c.find(f"{ns}v")
            if v is None:
                return None
            raw = v.text
            if t == "s" and raw is not None:
                i = int(raw)
                return sst[i] if i < len(sst) else raw
            return raw

        for s in wb.findall(f"{ns}sheets/{ns}sheet"):
            sname = s.attrib.get("name", "")
            if sname not in sheet_map:
                continue
            fid = sheet_map[sname]
            rid = s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = relmap[rid]
            sheet_xml = "xl/" + target.lstrip("/") if not target.startswith("xl/") else target
            root = ET.fromstring(z.read(sheet_xml))
            for row in root.findall(f".//{ns}row"):
                r = int(row.attrib.get("r", "0"))
                cells = {c.attrib.get("r", ""): cval(c) for c in row.findall(f"{ns}c")}
                vals = [cells.get(f"{col}{r}") for col in ["A", "B", "C", "D", "E", "F", "G"]]
                if r < 8:
                    continue
                param, desc, as_is, s1, s2, change, comments = vals
                if not param or str(param).strip().lower() == "parameter":
                    continue
                if not change:
                    continue
                ch = str(change).strip().lower()
                bucket = None
                if "major" in ch:
                    bucket = "major_change"
                elif ch == "change":
                    bucket = "change"
                elif "slight" in ch:
                    bucket = "slight_change"
                if bucket is None:
                    continue
                mapping[fid][bucket].append(
                    {
                        "parameter": str(param),
                        "description": str(desc or ""),
                        "as_is": str(as_is or ""),
                        "scenario_1": str(s1 or ""),
                        "scenario_2": str(s2 or ""),
                        "change": str(change),
                        "comments": str(comments or ""),
                    }
                )
    return mapping


def _enrich_dynamic_ui_parameters(
    ui: Dict[str, List[Dict[str, Any]]],
    mapping: Dict[str, Dict[str, list]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Attach change_bucket from Excel column F, else from Scenario Mapping workbook."""
    out: Dict[str, List[Dict[str, Any]]] = {"routes": [], "border": []}
    for fam in ("routes", "border"):
        pmap: Dict[str, str] = {}
        for bucket_key in ("major_change", "change", "slight_change"):
            for row in mapping.get(fam, {}).get(bucket_key, []) or []:
                p = str(row.get("parameter", "")).strip()
                if p:
                    pmap[p] = bucket_key
        for row in ui.get(fam) or []:
            r = dict(row)
            ex = r.get("change_bucket_excel") or ""
            if ex:
                r["change_bucket"] = ex
            else:
                r["change_bucket"] = pmap.get(str(r.get("label", "")).strip(), "unspecified")
            r.pop("change_bucket_excel", None)
            for k in ("pct_delta_scenario_1_vs_ideal", "pct_delta_scenario_2_vs_ideal"):
                v = r.get(k)
                if isinstance(v, float) and np.isnan(v):
                    r[k] = None
            out[fam].append(r)
    return out


def _attach_slider_specs(
    ui: Dict[str, List[Dict[str, Any]]],
    base: Dict[str, float],
) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {"routes": [], "border": []}
    for fam in ("routes", "border"):
        for row in ui.get(fam) or []:
            r = dict(row)
            r["slider"] = build_slider_metadata(
                str(r.get("label", "")),
                r.get("ideal"),
                r.get("scenario_1"),
                r.get("scenario_2"),
                base,
            )
            out[fam].append(r)
    return out


def _apply_dynamic_slider_values(
    x: Dict[str, float],
    family: str,
    sliders: Dict[str, float],
    ui_rows: List[Dict[str, Any]],
) -> Dict[str, float]:
    """Apply absolute-unit sliders (minutes, counts, capacity) after semantic Excel."""
    if not sliders:
        return x
    out = dict(x)
    by_id = {r["id"]: r for r in ui_rows}
    for pid, val in sliders.items():
        row = by_id.get(str(pid))
        if not row:
            continue
        spec = row.get("slider") or {}
        kind = spec.get("kind")
        if not kind:
            continue
        v = float(val)
        if kind == "check_doc_minutes":
            out["ChkTime_Doc"] = max(0.01, v)
        elif kind == "check_phy_minutes":
            out["ChkTime_Phy"] = max(0.01, v)
        elif kind == "count_integer":
            f = spec.get("feature")
            if f:
                out[f] = float(int(round(_clip(v, spec.get("min", 1.0), spec.get("max", 99.0)))))
        elif kind == "capacity":
            f = spec.get("feature")
            if f:
                out[f] = max(0.0, v)
    return out


class InferenceEngine:
    def __init__(self, outputs_dir: Path) -> None:
        self.outputs_dir = outputs_dir
        self.trained_dir = outputs_dir / "trained_models"
        self.selected_models = _load_selected_models(
            outputs_dir / "step4_shap" / "shap_selected_models.csv"
        )
        self.conformal = _load_json(outputs_dir / "conformal_results.json")
        self.scaler = joblib.load(self.trained_dir / "scaler.joblib")
        X, _ = load_xy()
        self.base = X[TRAINING_COLUMN_ORDER].mean(axis=0).astype(float).to_dict()
        self.scenario_mapping = _parse_xlsx_scenario_mapping(
            ROOT / "UI" / "Scenario Mapping product category ALStudents.xlsx"
        )
        self.dynamic_param_tables, self.dynamic_params_meta, self.dynamic_raw_params = load_dynamic_tables(
            ROOT
        )
        self.dynamic_ui_parameters = _attach_slider_specs(
            _enrich_dynamic_ui_parameters(
                self.dynamic_params_meta.get("ui_parameters") or {"routes": [], "border": []},
                self.scenario_mapping,
            ),
            self.base,
        )
        tc = list(TRAINING_COLUMN_ORDER)
        train_bounds = _bounds_from_frame(X, tc)
        self.feature_bounds: Dict[str, Tuple[float, float]] = dict(train_bounds)
        self.nolhc_designs_workbook: Optional[str] = None
        for pth in _nolhc_designs_candidates(ROOT):
            ob = _bounds_from_expvalues(pth, tc)
            if ob:
                self.feature_bounds = merge_bounds(self.feature_bounds, ob)
                self.nolhc_designs_workbook = str(pth.resolve())
                break
        for k in tc:
            if k not in self.feature_bounds:
                b = float(self.base[k])
                self.feature_bounds[k] = (b - 1.0, b + 1.0)
        self.input_sliders: List[Dict[str, Any]] = build_input_sliders(
            tc,
            self.feature_bounds,
            INPUT_DESCRIPTIONS,
            input_unit,
        )
        self.feature_defaults_by_scenario: Dict[str, Dict[str, Dict[str, float]]] = {}

    def compute_feature_defaults(
        self, level_inputs_map: Dict[str, Dict[str, Dict[str, float]]]
    ) -> Dict[str, Dict[str, Dict[str, float]]]:
        out: Dict[str, Dict[str, Dict[str, float]]] = {}
        for fam in ("routes", "border"):
            out[fam] = {}
            for lev in ("baseline", "moderate", "significant"):
                li = level_inputs_map[fam][lev]
                col = scenario_level_to_column(lev)
                x = self._vector_with_dynamic(fam, li, li, col, dynamic_sliders=None)
                out[fam][lev] = {k: float(x[k]) for k in TRAINING_COLUMN_ORDER}
        return out

    def _direct_model_vector(self, model_features: Dict[str, float]) -> Dict[str, float]:
        x = dict(self.base)
        for k, v in model_features.items():
            if k in TRAINING_COLUMN_ORDER:
                x[k] = clip_feature(k, float(v), self.feature_bounds, self.base)
        return x

    def _split_dynamic_sliders(
        self, sliders: Dict[str, float], family: str
    ) -> Tuple[Optional[Dict[str, float]], Dict[str, float]]:
        raw: Dict[str, float] = {}
        absolute: Dict[str, float] = {}
        by_id = {r["id"]: r for r in self.dynamic_ui_parameters.get(family) or []}
        for pid, val in sliders.items():
            row = by_id.get(str(pid))
            if not row:
                continue
            kind = (row.get("slider") or {}).get("kind")
            if kind in ("route_landbridge_pct", "percent_0_100", "preboard_pct", "generic_percent"):
                raw[str(row["label"])] = float(val)
            elif kind:
                absolute[str(pid)] = float(val)
        return (raw if raw else None), absolute

    def _vector_with_dynamic(
        self,
        family: str,
        inputs: Dict[str, float],
        level_inputs: Dict[str, float],
        excel_column: str,
        dynamic_sliders: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        x = self._scenario_vector(family, inputs, level_inputs)
        x = apply_dynamic_overrides(x, family, excel_column, self.dynamic_param_tables)
        raw_ov: Optional[Dict[str, float]] = None
        abs_sl: Dict[str, float] = {}
        if dynamic_sliders:
            raw_ov, abs_sl = self._split_dynamic_sliders(dynamic_sliders, family)
        x = apply_semantic_excel(
            x,
            family,
            excel_column,
            self.dynamic_raw_params,
            column_overrides=raw_ov,
        )
        if abs_sl:
            x = _apply_dynamic_slider_values(
                x,
                family,
                abs_sl,
                self.dynamic_ui_parameters.get(family) or [],
            )
        return x

    def _scenario_vector(
        self, family: str, inputs: Dict[str, float], level_inputs: Dict[str, float]
    ) -> Dict[str, float]:
        x = dict(self.base)
        p = dict(level_inputs)
        p.update({k: float(v) for k, v in inputs.items()})
        lb = _clip(float(p.get("landbridgeShare", 100.0)), 0.0, 100.0) / 100.0
        dr = 1.0 - lb

        # Keep total tonnage, reallocate route split strictly by scenario sliders.
        for total_key, lb_key, dr_key, shift_key in (
            ("NA_Im", "NA_Im_LB", "NA_Im_DR", "Shift_NA_Im_LB_to_Cher"),
            ("NA_Ex", "NA_Ex_LB", "NA_Ex_DR", "Shift_NA_Ex_LB_to_Cher"),
            ("A_Im", "A_Im_LB", "A_Im_DR", "Shift_A_Im_LB_to_Cher"),
            ("A_Ex", "A_Ex_LB", "A_Ex_DR", "Shift_A_Ex_LB_to_Cher"),
        ):
            total = float(x[total_key])
            x[lb_key] = total * lb
            x[dr_key] = total * dr
            x[shift_key] = total * dr

        if family == "routes":
            ntb_i = _clip(float(p.get("ntbIrish", 0.0)), 0.0, 100.0) / 100.0
            ntb_u = _clip(float(p.get("ntbUK", 0.0)), 0.0, 100.0) / 100.0
            ntb = 0.5 * (ntb_i + ntb_u)
            x["ChkTime_Doc"] = float(x["ChkTime_Doc"]) * (1.0 + 1.8 * ntb)
            x["ChkTime_Phy"] = float(x["ChkTime_Phy"]) * (1.0 + 1.5 * ntb)
            for k in ("Pct_NA_OB_Red", "Pct_A_OB_Red", "Pct_NA_IB_Red", "Pct_A_IB_Red"):
                x[k] = _clip(float(x[k]) + 0.25 * ntb, 0.0, 1.0)
            x["Pct_NA_OB_Green"] = _clip(1.0 - x["Pct_NA_OB_Red"], 0.0, 1.0)
            x["Pct_NA_IB_Green"] = _clip(1.0 - x["Pct_NA_IB_Red"], 0.0, 1.0)
            x["Pct_IB_PreBoard"] = _clip(float(x["Pct_IB_PreBoard"]) + 0.2 * ntb, 0.0, 1.0)
            x["Pct_OB_PreBoard"] = _clip(float(x["Pct_OB_PreBoard"]) + 0.2 * ntb, 0.0, 1.0)
        else:
            enh = _clip(float(p.get("inspectionEnhance", 0.0)), 0.0, 100.0) / 100.0
            cov = _clip(float(p.get("inspectionCoverage", 0.0)), 0.0, 100.0) / 100.0
            strength = enh * cov
            x["ChkTime_Doc"] = float(x["ChkTime_Doc"]) * (1.0 - 0.7 * strength)
            x["ChkTime_Phy"] = float(x["ChkTime_Phy"]) * (1.0 - 0.6 * strength)
            x["NumCusShed_D"] = float(x["NumCusShed_D"]) * (1.0 + 0.5 * strength)
            x["NumCusShed_R"] = float(x["NumCusShed_R"]) * (1.0 + 0.5 * strength)
            x["NumDAFM_D"] = float(x["NumDAFM_D"]) * (1.0 + 0.5 * strength)
            x["NumDAFM_R"] = float(x["NumDAFM_R"]) * (1.0 + 0.5 * strength)
            for k in ("Pct_NA_OB_Red", "Pct_A_OB_Red", "Pct_NA_IB_Red", "Pct_A_IB_Red"):
                x[k] = _clip(float(x[k]) * (1.0 - 0.35 * strength), 0.0, 1.0)
            x["Pct_NA_OB_Green"] = _clip(1.0 - x["Pct_NA_OB_Red"], 0.0, 1.0)
            x["Pct_NA_IB_Green"] = _clip(1.0 - x["Pct_NA_IB_Red"], 0.0, 1.0)
            x["Pct_IB_PreBoard"] = _clip(float(x["Pct_IB_PreBoard"]) * (1.0 - 0.4 * strength), 0.0, 1.0)
            x["Pct_OB_PreBoard"] = _clip(float(x["Pct_OB_PreBoard"]) * (1.0 - 0.4 * strength), 0.0, 1.0)

        return x

    def _predict_target(self, target: str, model: str, x_row: np.ndarray, x_scaled: np.ndarray) -> float:
        tdir = self.trained_dir / _safe_filename(target)
        est = joblib.load(tdir / f"{_safe_filename(model)}.joblib")
        if model in NEEDS_SCALING:
            return float(est.predict(x_scaled)[0])
        return float(est.predict(x_row)[0])

    def _predict_all_targets(self, xmap: Dict[str, float]) -> Dict[str, float]:
        x_row = np.array([[float(xmap[c]) for c in TRAINING_COLUMN_ORDER]], dtype=float)
        x_scaled = self.scaler.transform(x_row)
        out: Dict[str, float] = {}
        for target, model in self.selected_models.items():
            raw = self._predict_target(target, model, x_row, x_scaled)
            out[target] = _clip_target_output(target, raw)
        return out

    def _monte_carlo(
        self,
        family: str,
        inputs: Dict[str, float],
        level_inputs: Dict[str, float],
        *,
        focus_target: str,
        excel_column: str,
        dynamic_sliders: Optional[Dict[str, float]] = None,
        n_samples: int = 250,
        seed: int = 42,
        feature_center: Optional[Dict[str, float]] = None,
        use_direct_features: bool = False,
    ) -> Dict[str, Any]:
        rng = np.random.default_rng(seed)
        if focus_target not in self.selected_models:
            return {"target": focus_target, "bins": [], "counts": [], "mean": 0.0, "p10": 0.0, "p90": 0.0}
        model = self.selected_models[focus_target]
        vals = []
        for _ in range(n_samples):
            if use_direct_features and feature_center is not None:
                perturbed = dict(feature_center)
                for c in TRAINING_COLUMN_ORDER:
                    lo, hi = self.feature_bounds[c]
                    span = hi - lo
                    if span <= 0:
                        span = 1.0
                    perturbed[c] = _clip(
                        float(perturbed[c]) + rng.normal(0.0, 0.06 * span),
                        lo,
                        hi,
                    )
                xmap = perturbed
            else:
                perturbed = dict(inputs)
                for k, v in list(perturbed.items()):
                    base = float(v)
                    jitter = rng.normal(0.0, 3.0)
                    perturbed[k] = _clip(base + jitter, 0.0, 100.0)
                xmap = self._vector_with_dynamic(
                    family, perturbed, level_inputs, excel_column, dynamic_sliders=dynamic_sliders
                )
            x_row = np.array([[float(xmap[c]) for c in TRAINING_COLUMN_ORDER]], dtype=float)
            x_scaled = self.scaler.transform(x_row)
            vals.append(self._predict_target(focus_target, model, x_row, x_scaled))
        arr = np.asarray(vals, dtype=float)
        counts, edges = np.histogram(arr, bins=8)
        bins = [f"{edges[i]:.2f}-{edges[i+1]:.2f}" for i in range(len(edges) - 1)]
        return {
            "target": focus_target,
            "model": model,
            "bins": bins,
            "counts": counts.astype(int).tolist(),
            "mean": float(arr.mean()),
            "p10": float(np.percentile(arr, 10)),
            "p90": float(np.percentile(arr, 90)),
            "n_samples": int(n_samples),
        }

    def _monte_carlo_target_correlation(
        self,
        family: str,
        inputs: Dict[str, float],
        level_inputs: Dict[str, float],
        excel_column: str,
        targets: List[str],
        *,
        dynamic_sliders: Optional[Dict[str, float]] = None,
        n_samples: int = 96,
        seed: int = 43,
        feature_center: Optional[Dict[str, float]] = None,
        use_direct_features: bool = False,
    ) -> Dict[str, Any]:
        rng = np.random.default_rng(seed)
        targets = [t for t in targets if t in self.selected_models]
        if len(targets) < 2:
            return {"targets": targets, "matrix": [], "n_samples": 0}
        mat = np.zeros((n_samples, len(targets)), dtype=float)
        for s in range(n_samples):
            if use_direct_features and feature_center is not None:
                perturbed = dict(feature_center)
                for c in TRAINING_COLUMN_ORDER:
                    lo, hi = self.feature_bounds[c]
                    span = hi - lo
                    if span <= 0:
                        span = 1.0
                    perturbed[c] = _clip(
                        float(perturbed[c]) + rng.normal(0.0, 0.06 * span),
                        lo,
                        hi,
                    )
                xmap = perturbed
            else:
                perturbed = dict(inputs)
                for k, v in list(perturbed.items()):
                    perturbed[k] = _clip(float(v) + rng.normal(0.0, 3.0), 0.0, 100.0)
                xmap = self._vector_with_dynamic(
                    family, perturbed, level_inputs, excel_column, dynamic_sliders=dynamic_sliders
                )
            x_row = np.array([[float(xmap[c]) for c in TRAINING_COLUMN_ORDER]], dtype=float)
            x_scaled = self.scaler.transform(x_row)
            for j, t in enumerate(targets):
                model = self.selected_models[t]
                mat[s, j] = self._predict_target(t, model, x_row, x_scaled)
        corr = np.corrcoef(mat.T)
        corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
        return {
            "targets": targets,
            "matrix": corr.tolist(),
            "n_samples": int(n_samples),
        }

    def _trend_12m(
        self,
        x0map: Dict[str, float],
        xmap: Dict[str, float],
    ) -> Dict[str, Dict[str, list[float]]]:
        trend: Dict[str, Dict[str, list[float]]] = {}
        for m in range(1, 13):
            alpha = m / 12.0
            blended = {
                c: float(x0map[c]) + alpha * (float(xmap[c]) - float(x0map[c]))
                for c in TRAINING_COLUMN_ORDER
            }
            preds = self._predict_all_targets(blended)
            for target, y in preds.items():
                conf = (self.conformal.get(target, {}) or {}).get(self.selected_models[target], {})
                q = float(conf.get("quantile", 0.0))
                if target not in trend:
                    trend[target] = {"point": [], "lower": [], "upper": []}
                trend[target]["point"].append(float(y))
                trend[target]["lower"].append(float(_clip_target_output(target, y - q)))
                trend[target]["upper"].append(float(_clip_target_output(target, y + q)))
        return trend

    def infer(
        self,
        family: str,
        inputs: Dict[str, float],
        level_inputs: Dict[str, float],
        *,
        baseline_inputs: Dict[str, float],
        scenario_level: str = "baseline",
        focus_target: str = "TT_OB_Agri",
        include_target_corr: bool = False,
        heatmap_targets: Optional[List[str]] = None,
        dynamic_sliders: Optional[Dict[str, float]] = None,
        include_trend: bool = True,
        mc_samples: int = 200,
        model_features: Optional[Dict[str, float]] = None,
        output_targets: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        excel_col = scenario_level_to_column(scenario_level)
        use_direct = model_features is not None and len(model_features) > 0
        if use_direct:
            xmap = self._direct_model_vector(model_features or {})
        else:
            xmap = self._vector_with_dynamic(
                family, inputs, level_inputs, excel_col, dynamic_sliders=dynamic_sliders
            )
        x_row = np.array([[float(xmap[c]) for c in TRAINING_COLUMN_ORDER]], dtype=float)
        x_scaled = self.scaler.transform(x_row)
        # Pre-Brexit reference: AS-IS workbook column only (no user slider tweaks).
        x0map = self._vector_with_dynamic(
            family, baseline_inputs, baseline_inputs, "as_is", dynamic_sliders=None
        )
        base_row = np.array([[float(x0map[c]) for c in TRAINING_COLUMN_ORDER]], dtype=float)
        base_scaled = self.scaler.transform(base_row)

        targets_to_run = list(self.selected_models.items())
        if output_targets:
            want = {str(x) for x in output_targets}
            targets_to_run = [(t, m) for t, m in targets_to_run if t in want]
        preds: Dict[str, Any] = {}
        for target, model in targets_to_run:
            raw_y = self._predict_target(target, model, x_row, x_scaled)
            raw_y0 = self._predict_target(target, model, base_row, base_scaled)
            y = _clip_target_output(target, raw_y)
            y0 = _clip_target_output(target, raw_y0)
            clipped = (y != raw_y) or (y0 != raw_y0)

            conf = (self.conformal.get(target, {}) or {}).get(model, {})
            q = float(conf.get("quantile", 0.0))
            lower = _clip_target_output(target, y - q)
            upper = _clip_target_output(target, y + q)
            preds[target] = {
                "model": model,
                "prediction": y,
                "baseline_prediction": y0,
                "delta_vs_baseline": y - y0,
                "interval": {"lower": lower, "upper": upper, "width": max(0.0, upper - lower)},
                "coverage_level": float(conf.get("coverage_level", 0.9)),
                "empirical_coverage": float(conf.get("empirical_coverage", 0.0)),
                "clipped_to_domain": bool(clipped),
            }
        mc = self._monte_carlo(
            family,
            inputs,
            level_inputs,
            focus_target=focus_target,
            excel_column=excel_col,
            dynamic_sliders=None if use_direct else dynamic_sliders,
            n_samples=mc_samples,
            feature_center=xmap,
            use_direct_features=use_direct,
        )
        trend: Dict[str, Any] = {}
        if include_trend:
            trend = self._trend_12m(x0map, xmap)
        out: Dict[str, Any] = {
            "vector": xmap,
            "predictions": preds,
            "monte_carlo": mc,
            "trend_12m": trend,
            "excel_column": excel_col,
            "dynamic_params": self.dynamic_params_meta,
            "use_direct_model_features": use_direct,
        }
        if include_target_corr:
            ht = heatmap_targets if heatmap_targets else list(OUTPUT_COLUMN_ORDER)
            out["target_correlation"] = self._monte_carlo_target_correlation(
                family,
                inputs,
                level_inputs,
                excel_col,
                ht,
                dynamic_sliders=None if use_direct else dynamic_sliders,
                feature_center=xmap,
                use_direct_features=use_direct,
            )
        return out


class Handler(SimpleHTTPRequestHandler):
    engine: InferenceEngine
    level_inputs: Dict[str, Dict[str, Dict[str, float]]]

    @staticmethod
    def _path_only(raw: str) -> str:
        """Strip query string / fragment — ``self.path`` may include ``?query``."""
        if not raw:
            return "/"
        p = raw.split("?", 1)[0].split("#", 1)[0]
        return p or "/"

    def end_headers(self) -> None:  # noqa: N802
        # Prevent stale cached ES modules during UI dev (avoids "header only" blank pages after edits).
        try:
            p = self._path_only(self.path)
            if p.startswith("/UI/") and p.endswith(
                (".js", ".mjs", ".html", ".css", ".json", ".map", ".svg")
            ):
                self.send_header("Cache-Control", "no-store, must-revalidate")
        except Exception:
            pass
        super().end_headers()

    def _json(self, payload: Dict[str, Any], status: int = 200) -> None:
        try:
            body = json.dumps(_json_sanitize(payload)).encode("utf-8")
        except (TypeError, ValueError) as e:
            body = json.dumps(
                {"ok": False, "error": f"JSON serialization failed: {e}"}
            ).encode("utf-8")
            status = 500
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, OSError):
            # Client closed the connection (navigation, duplicate request, timeout).
            pass

    def do_POST(self) -> None:  # noqa: N802
        p = self._path_only(self.path)
        if p not in ("/api/infer", "/api/predict"):
            self._json({"error": "not_found"}, status=404)
            return
        n = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(n)
        try:
            req = json.loads(raw.decode("utf-8"))
            p = _parse_infer_request_body(req)
            family = p["family"]
            level = p["level"]
            inputs = p["inputs"]
            level_base = self.level_inputs[family][level]
            baseline_base = self.level_inputs[family]["baseline"]
            out = self.engine.infer(
                family,
                inputs,
                level_base,
                baseline_inputs=baseline_base,
                scenario_level=level,
                focus_target=p["focus_target"],
                include_target_corr=p["include_target_corr"],
                heatmap_targets=p["heatmap_targets"],
                dynamic_sliders=p["dynamic_sliders"],
                include_trend=p["include_trend"],
                mc_samples=p["mc_samples"],
                model_features=p["model_features"],
                output_targets=p["output_targets"],
            )
            if self.path == "/api/predict":
                self._json(
                    {
                        "ok": True,
                        "stack": {
                            "pipeline": "experimenting_ml",
                            "outputs_dir": str(self.engine.outputs_dir),
                            "selected_models": dict(self.engine.selected_models),
                        },
                        "predictions": out["predictions"],
                        "simulator": _build_simulator_payload(out["predictions"]),
                        "monte_carlo": out.get("monte_carlo"),
                        "trend_12m": out.get("trend_12m"),
                        "vector": out.get("vector"),
                        "excel_column": out.get("excel_column"),
                        "use_direct_model_features": out.get("use_direct_model_features"),
                        "dynamic_params": out.get("dynamic_params"),
                    }
                )
            else:
                self._json({"ok": True, **out})
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        except Exception as e:  # noqa: BLE001
            try:
                self._json({"ok": False, "error": str(e)}, status=400)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

    def do_GET(self) -> None:  # noqa: N802
        p = self._path_only(self.path)
        if p == "/api/health":
            self._json(
                {
                    "ok": True,
                    "backend_connected": True,
                    "model_loaded": True,
                    "n_targets": len(self.engine.selected_models),
                }
            )
            return
        if p == "/api/meta":
            self._json(
                {
                    "ok": True,
                    "selected_models": dict(self.engine.selected_models),
                    "feature_descriptions": INPUT_DESCRIPTIONS,
                    "target_descriptions": OUTPUT_DESCRIPTIONS,
                    "output_column_order": OUTPUT_COLUMN_ORDER,
                    "scenario_mapping": self.engine.scenario_mapping,
                    "dynamic_params": self.engine.dynamic_params_meta,
                    "dynamic_ui_parameters": self.engine.dynamic_ui_parameters,
                    "training_column_order": list(TRAINING_COLUMN_ORDER),
                    "input_sliders": self.engine.input_sliders,
                    "feature_bounds": {k: list(v) for k, v in self.engine.feature_bounds.items()},
                    "feature_defaults_by_scenario": self.engine.feature_defaults_by_scenario,
                    "nolhc_designs_workbook": self.engine.nolhc_designs_workbook,
                    "scenario_families": {
                        "routes": {
                            "title": "Direct route scenario",
                            "excel_sheet": "Direct Route Scenario",
                            "levels": {
                                "baseline": "Pre-Brexit baseline (As-Is)",
                                "moderate": "Moderate shift to direct route",
                                "significant": "Significant shift to direct route",
                            },
                        },
                        "border": {
                            "title": "Non-tariff scenario (border operations)",
                            "excel_sheet": "Non-Tarriff Barrier",
                            "levels": {
                                "baseline": "Pre-Brexit baseline (As-Is)",
                                "moderate": "Moderate enhancement in border operations",
                                "significant": "Significant enhancement in border operations",
                            },
                        },
                    },
                }
            )
            return
        super().do_GET()


def main() -> None:
    p = argparse.ArgumentParser(description="Serve UI + strict model inference API")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--host", default="127.0.0.1")
    args = p.parse_args()

    outputs = ROOT / "outputs"
    engine = InferenceEngine(outputs)

    level_inputs: Dict[str, Dict[str, Dict[str, float]]] = {
        "routes": {
            "baseline": {"directShare": 0.0, "landbridgeShare": 100.0, "ntbIrish": 0.0, "ntbUK": 0.0},
            "moderate": {"directShare": 40.0, "landbridgeShare": 60.0, "ntbIrish": 40.0, "ntbUK": 40.0},
            "significant": {"directShare": 85.0, "landbridgeShare": 15.0, "ntbIrish": 80.0, "ntbUK": 80.0},
        },
        "border": {
            "baseline": {"inspectionEnhance": 0.0, "landbridgeShare": 100.0, "inspectionCoverage": 0.0},
            "moderate": {"inspectionEnhance": 40.0, "landbridgeShare": 100.0, "inspectionCoverage": 40.0},
            "significant": {"inspectionEnhance": 80.0, "landbridgeShare": 100.0, "inspectionCoverage": 80.0},
        },
    }

    engine.feature_defaults_by_scenario = engine.compute_feature_defaults(level_inputs)

    Handler.engine = engine
    Handler.level_inputs = level_inputs
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Serving on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

