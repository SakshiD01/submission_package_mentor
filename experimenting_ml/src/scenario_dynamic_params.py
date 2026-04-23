"""
Load the dynamic-parameters workbook (e.g. ``scenario based dynamic input parameter.xlsx``
or ``scenario based dynamic input parameters.xlsx``) and map rows to NOLHC feature columns.

Sheets mirror the scenario mapping workbook: 'Direct Route Scenario' -> routes,
'Non-Tarriff Barrier' -> border. Columns A–G: Parameter, Description, AS-IS,
Scenario 1, Scenario 2, Change, Comments.

If the workbook is missing or a parameter is unmapped, inference falls back to
slider-driven _scenario_vector() only.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zipfile import ZipFile

from training_columns import TRAINING_COLUMN_ORDER

# Older mapping workbook used "Direct Route Scenario" / "Non-Tarriff Barrier"; dynamic-input file may use "… Family".
SHEET_TO_FAMILY = {
    "Direct Route Scenario": "routes",
    "Direct Route Family": "routes",
    "Non-Tarriff Barrier": "border",
    "Non-Tarriff Barrier Family": "border",
    "Non-Tariff Barrier": "border",
    "Non-Tariff Barrier Family": "border",
}

COLUMN_KEYS = ("as_is", "scenario_1", "scenario_2")

# Excel parameter codes -> NOLHC training feature name (extend as your workbook evolves).
EXCEL_PARAM_ALIASES: Dict[str, str] = {
    # Direct / common naming
    "ChkTime_Doc": "ChkTime_Doc",
    "ChkTime_Phy": "ChkTime_Phy",
    "DocChkTimeAPImIR": "ChkTime_Doc",
    "PhyChkTimeAPImIR": "ChkTime_Phy",
    "IdnChkTimeAPImIR": "ChkTime_Doc",
    "SecChkTimeAPImIR": "ChkTime_Doc",
    "NumCusShed_D": "NumCusShed_D",
    "NumCusShed_R": "NumCusShed_R",
    "NumDAFM_D": "NumDAFM_D",
    "NumDAFM_R": "NumDAFM_R",
    "VCap_Dub_Hey": "VCap_Dub_Hey",
    "VCap_Dub_Holy": "VCap_Dub_Holy",
    "VCap_Dub_Liv": "VCap_Dub_Liv",
    "VCap_Ross_Fish": "VCap_Ross_Fish",
    "VCap_Ross_Pem": "VCap_Ross_Pem",
    # Green / red / pre-board shares
    "PerGreenTrucksAPImIR": "Pct_NA_IB_Green",
    "PerGreenTrucksAPExIR": "Pct_NA_OB_Green",
    "PerPhyChkAPImIR": "Pct_NA_IB_Red",
    "PerFullIdnChkAPImIR": "Pct_NA_IB_Red",
    "PerSecurityChkAPIR": "Pct_IB_PreBoard",
    "PerUKTrucksMoveD": "Pct_OB_PreBoard",
    "PerLBTrucksMoveD": "Pct_IB_PreBoard",
    # Volumes (if present as single totals)
    "VolAllPImUK": "NA_Im",
    "VolAllPExUK": "NA_Ex",
    "VolAllAImUK": "A_Im",
    "VolAllAExUK": "A_Ex",
}


def _dynamic_xlsx_candidates(root: Path) -> List[Path]:
    ui = root / "UI"
    names = [
        "scenario based dynamic input param final.xlsx",
        "scenario based dynamic input parameter.xlsx",
        "scenario based dynamic input parameters.xlsx",
        "scenario_based_dynamic_input_parameters.xlsx",
    ]
    out: List[Path] = []
    for n in names:
        p = ui / n
        if p.is_file():
            out.append(p)
    if ui.is_dir():
        for p in sorted(ui.glob("*.xlsx")):
            if p.name.startswith("~$"):
                continue
            low = p.name.lower()
            if "dynamic" in low and "scenario" in low and p not in out:
                out.append(p)
    return out


def _clip(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))


def _parse_numeric_cell(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.lower() in {"nan", "none", "n/a", "-"}:
        return None
    s = s.replace("%", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        m = re.search(r"[-+]?\d*\.?\d+", s)
        if m:
            try:
                return float(m.group(0))
            except ValueError:
                return None
        return None


def _normalize_feature_value(feature: str, val: float) -> float:
    """Map Excel display units to model units (proportions often 0–100 in sheets)."""
    if feature.startswith("Pct_") or feature in ("Pct_IB_PreBoard", "Pct_OB_PreBoard"):
        if val > 1.5:
            return _clip(val / 100.0, 0.0, 1.0)
        return _clip(val, 0.0, 1.0)
    return val


def _slug_param(pkey: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", pkey.strip().lower()).strip("_")
    return (s[:96] if s else "param")


def _normalize_change_bucket_cell(raw: Any) -> str:
    """Map Excel column F (Change) to major_change | change | slight_change | ''."""
    if raw is None:
        return ""
    s = str(raw).strip().lower()
    if not s:
        return ""
    if "major" in s:
        return "major_change"
    if "slight" in s:
        return "slight_change"
    if s == "change" or ("change" in s and "major" not in s and "slight" not in s):
        return "change"
    return ""


def _pct_delta_vs_ideal(ideal: Optional[float], cur: Optional[float]) -> Optional[float]:
    if ideal is None or cur is None:
        return None
    if ideal == 0:
        return None
    return float(((cur - ideal) / abs(ideal)) * 100.0)


def _resolve_feature(param: str) -> Optional[str]:
    p = str(param).strip()
    if not p:
        return None
    if p in TRAINING_COLUMN_ORDER:
        return p
    return EXCEL_PARAM_ALIASES.get(p)


def parse_dynamic_params_xlsx(
    xlsx_path: Path,
) -> Tuple[Dict[str, Dict[str, Dict[str, float]]], Dict[str, Any], Dict[str, Dict[str, Dict[str, float]]]]:
    """
    Returns:
      tables[family][column_key][feature_name] = float
      meta
      raw_params[family][column_key][parameter_label] = float (every numeric row)
    """
    empty: Dict[str, Dict[str, Dict[str, float]]] = {
        "routes": {k: {} for k in COLUMN_KEYS},
        "border": {k: {} for k in COLUMN_KEYS},
    }
    raw_params: Dict[str, Dict[str, Dict[str, float]]] = {
        "routes": {k: {} for k in COLUMN_KEYS},
        "border": {k: {} for k in COLUMN_KEYS},
    }
    if not xlsx_path.is_file():
        return (
            empty,
            {
                "path": str(xlsx_path),
                "loaded": False,
                "reason": "missing",
                "ui_parameters": {"routes": [], "border": []},
            },
            raw_params,
        )

    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    unmapped_samples: List[str] = []
    row_counts = {"routes": 0, "border": 0}
    ui_parameters: Dict[str, List[Dict[str, Any]]] = {"routes": [], "border": []}

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
            if sname not in SHEET_TO_FAMILY:
                continue
            fid = SHEET_TO_FAMILY[sname]
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
                param, desc, as_is, s1, s2, change_cell, comments_cell = vals
                if not param or str(param).strip().lower() == "parameter":
                    continue
                pkey = str(param).strip()
                triple = (
                    _parse_numeric_cell(as_is),
                    _parse_numeric_cell(s1),
                    _parse_numeric_cell(s2),
                )
                has_any = any(triple[i] is not None for i in range(3))
                if has_any:
                    iv, s1v, s2v = triple[0], triple[1], triple[2]
                    ui_parameters[fid].append(
                        {
                            "id": _slug_param(pkey),
                            "label": pkey,
                            "description": str(desc or "").strip(),
                            "ideal": iv,
                            "scenario_1": s1v,
                            "scenario_2": s2v,
                            "change_bucket_excel": _normalize_change_bucket_cell(change_cell),
                            "comments": str(comments_cell or "").strip(),
                            "pct_delta_scenario_1_vs_ideal": _pct_delta_vs_ideal(iv, s1v),
                            "pct_delta_scenario_2_vs_ideal": _pct_delta_vs_ideal(iv, s2v),
                        }
                    )
                for i, ck in enumerate(COLUMN_KEYS):
                    v = triple[i]
                    if v is None:
                        continue
                    raw_params[fid][ck][pkey] = float(v)

                feat = _resolve_feature(param)
                if feat is None:
                    if len(unmapped_samples) < 40:
                        unmapped_samples.append(pkey)
                    continue
                row_counts[fid] += 1
                for i, ck in enumerate(COLUMN_KEYS):
                    v = triple[i]
                    if v is None:
                        continue
                    empty[fid][ck][feat] = _normalize_feature_value(feat, float(v))

    meta: Dict[str, Any] = {
        "path": str(xlsx_path.resolve()),
        "loaded": True,
        "row_counts": row_counts,
        "unmapped_parameter_samples": unmapped_samples,
        "raw_parameter_counts": {
            "routes": {ck: len(raw_params["routes"][ck]) for ck in COLUMN_KEYS},
            "border": {ck: len(raw_params["border"][ck]) for ck in COLUMN_KEYS},
        },
        "ui_parameters": ui_parameters,
    }
    return empty, meta, raw_params


def load_dynamic_tables(
    root: Path,
) -> Tuple[Dict[str, Dict[str, Dict[str, float]]], Dict[str, Any], Dict[str, Dict[str, Dict[str, float]]]]:
    for path in _dynamic_xlsx_candidates(root):
        tables, meta, raw = parse_dynamic_params_xlsx(path)
        if meta.get("loaded"):
            return tables, meta, raw
    stub_path = root / "UI" / "scenario based dynamic input parameter.xlsx"
    empty = {
        "routes": {k: {} for k in COLUMN_KEYS},
        "border": {k: {} for k in COLUMN_KEYS},
    }
    raw_empty: Dict[str, Dict[str, Dict[str, float]]] = {
        "routes": {k: {} for k in COLUMN_KEYS},
        "border": {k: {} for k in COLUMN_KEYS},
    }
    return (
        empty,
        {
            "path": str(stub_path),
            "loaded": False,
            "reason": "no_workbook_found",
            "ui_parameters": {"routes": [], "border": []},
        },
        raw_empty,
    )


def scenario_level_to_column(level: str) -> str:
    if level == "moderate":
        return "scenario_1"
    if level == "significant":
        return "scenario_2"
    return "as_is"


ROUTE_SPLIT_PAIRS: Tuple[Tuple[str, str, str, str, str, str], ...] = (
    ("NA_Im", "NA_Im_LB", "NA_Im_DR", "Shift_NA_Im_LB_to_Cher", "Non-Agri Import LandBridge", "Non-Agri Import Direct Route"),
    ("NA_Ex", "NA_Ex_LB", "NA_Ex_DR", "Shift_NA_Ex_LB_to_Cher", "Non-Agri Export LandBridge", "Non-Agri Export Direct Route"),
    ("A_Im", "A_Im_LB", "A_Im_DR", "Shift_A_Im_LB_to_Cher", "Agri Import LandBridge", "Agri Import Direct Route"),
    ("A_Ex", "A_Ex_LB", "A_Ex_DR", "Shift_A_Ex_LB_to_Cher", "Agri Export LandBridge", "Agri Export Direct Route"),
)

VCAP_LABELS: Dict[str, str] = {
    "Vessel capacity from Dublin to Hey": "VCap_Dub_Hey",
    "Vessel capacity from Dublin to Holy": "VCap_Dub_Holy",
    "Vessel capacity from Dublin to Liv": "VCap_Dub_Liv",
    "Vessel capacity from Rosslare to Fish": "VCap_Ross_Fish",
    "Vessel capacity from Rosslare to Pem": "VCap_Ross_Pem",
}

COUNT_LABELS: Dict[str, str] = {
    "Number of Custom shed Dublin": "NumCusShed_D",
    "Number of DAFM Bays Dublin": "NumDAFM_D",
    "Number of Custom shed Rosslare": "NumCusShed_R",
    "Number of DAFM Bays Rosslare": "NumDAFM_R",
}

PCT_LABELS: Tuple[Tuple[str, str], ...] = (
    ("Pecentage of non-agri outbound green route trucks", "Pct_NA_OB_Green"),
    ("Pecentage of non-agri outbound red route trucks", "Pct_NA_OB_Red"),
    ("Pecentage of agri outbound red route trucks", "Pct_A_OB_Red"),
    ("Pecentage of non-agri inbound green route trucks", "Pct_NA_IB_Green"),
    ("Pecentage of non-agri inbound red route trucks", "Pct_NA_IB_Red"),
    ("Pecentage of agri inbound red route trucks", "Pct_A_IB_Red"),
)


def _pct01(val: float) -> float:
    v = float(val)
    if v > 1.5:
        return _clip(v / 100.0, 0.0, 1.0)
    return _clip(v, 0.0, 1.0)


def build_slider_metadata(
    label: str,
    ideal: Optional[float],
    s1: Optional[float],
    s2: Optional[float],
    base: Dict[str, float],
) -> Optional[Dict[str, Any]]:
    """
    UI slider spec: kinds route_landbridge_pct | check_doc_minutes | check_phy_minutes |
    count_integer | capacity | percent_0_100 | preboard_pct. Returns None for derived (e.g. Direct Route row).
    """
    lab = label.strip()
    for _tot, _lbk, _drk, _sk, _lbname, drn in ROUTE_SPLIT_PAIRS:
        if lab == drn:
            return None
    for _tot, _lbk, _drk, _sk, lbname, _drn in ROUTE_SPLIT_PAIRS:
        if lab == lbname:
            return {
                "kind": "route_landbridge_pct",
                "min": 0.0,
                "max": 100.0,
                "step": 1.0,
                "unit": "%",
                "defaults": {
                    "baseline": float(ideal if ideal is not None else 0.0),
                    "moderate": float(s1 if s1 is not None else ideal or 0.0),
                    "significant": float(s2 if s2 is not None else ideal or 0.0),
                },
            }

    low = lab.lower()
    if "check timings for document" in low or ("document" in low and "seal" in low):
        b = float(base.get("ChkTime_Doc", 1.0))

        def dm(pct: Optional[float]) -> float:
            p = float(pct or 0.0)
            return round(b * (1.0 + p / 100.0), 3)

        return {
            "kind": "check_doc_minutes",
            "min": max(0.05, b * 0.1),
            "max": b * 8.0,
            "step": 0.25,
            "unit": "min",
            "model_baseline_minutes": b,
            "defaults": {
                "baseline": dm(ideal),
                "moderate": dm(s1),
                "significant": dm(s2),
            },
        }

    if low.startswith("check timings for physical") or (
        "physical" in low and "check" in low and "document" not in low
    ):
        b = float(base.get("ChkTime_Phy", 1.0))

        def pm(pct: Optional[float]) -> float:
            p = float(pct or 0.0)
            return round(b * (1.0 + p / 100.0), 3)

        return {
            "kind": "check_phy_minutes",
            "min": max(0.05, b * 0.1),
            "max": b * 8.0,
            "step": 0.25,
            "unit": "min",
            "model_baseline_minutes": b,
            "defaults": {
                "baseline": pm(ideal),
                "moderate": pm(s1),
                "significant": pm(s2),
            },
        }

    for lbl, feat in COUNT_LABELS.items():
        if lab == lbl:
            iv = float(ideal if ideal is not None else base.get(feat, 1.0))
            return {
                "kind": "count_integer",
                "feature": feat,
                "min": max(1.0, iv - 10.0),
                "max": iv + 20.0,
                "step": 1.0,
                "unit": "count",
                "defaults": {
                    "baseline": float(ideal if ideal is not None else iv),
                    "moderate": float(s1 if s1 is not None else ideal if ideal is not None else iv),
                    "significant": float(s2 if s2 is not None else ideal if ideal is not None else iv),
                },
            }

    for lbl, feat in VCAP_LABELS.items():
        if lab == lbl:
            iv = float(ideal if ideal is not None else base.get(feat, 100.0))
            return {
                "kind": "capacity",
                "feature": feat,
                "min": max(0.0, iv * 0.4),
                "max": iv * 2.5,
                "step": 1.0,
                "unit": "trailers",
                "defaults": {
                    "baseline": float(ideal if ideal is not None else iv),
                    "moderate": float(s1 if s1 is not None else ideal if ideal is not None else iv),
                    "significant": float(s2 if s2 is not None else ideal if ideal is not None else iv),
                },
            }

    for lbl, feat in PCT_LABELS:
        if lab == lbl:
            b100 = float(base.get(feat, 0.0) * 100.0)

            def pv(x: Optional[float]) -> float:
                return float(x) if x is not None else b100

            return {
                "kind": "percent_0_100",
                "feature": feat,
                "min": 0.0,
                "max": 100.0,
                "step": 0.5,
                "unit": "%",
                "defaults": {
                    "baseline": pv(ideal),
                    "moderate": pv(s1),
                    "significant": pv(s2),
                },
            }

    if "pre-bording" in low or "pre-board" in low or "prebording" in low:
        inbound = "inbound" in low
        feat = "Pct_IB_PreBoard" if inbound else "Pct_OB_PreBoard"
        b100 = float(base.get(feat, 0.0) * 100.0)

        def pv(x: Optional[float]) -> float:
            return float(x) if x is not None else b100

        return {
            "kind": "preboard_pct",
            "feature": feat,
            "min": 0.0,
            "max": 100.0,
            "step": 0.5,
            "unit": "%",
            "defaults": {
                "baseline": pv(ideal),
                "moderate": pv(s1),
                "significant": pv(s2),
            },
        }

    if ideal is not None and 0.0 <= float(ideal) <= 100.0:
        return {
            "kind": "generic_percent",
            "min": 0.0,
            "max": 100.0,
            "step": 1.0,
            "unit": "%",
            "defaults": {
                "baseline": float(ideal),
                "moderate": float(s1 if s1 is not None else ideal),
                "significant": float(s2 if s2 is not None else ideal),
            },
        }
    return None


def apply_semantic_excel(
    x: Dict[str, float],
    family: str,
    column: str,
    raw: Dict[str, Dict[str, Dict[str, float]]],
    column_overrides: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Apply workbook rows that use human-readable labels (route % splits, capacities, etc.).
    Must run after _scenario_vector and apply_dynamic_overrides.
    column_overrides: optional label -> value merged into the active column (same units as Excel).
    """
    col = dict(raw.get(family, {}).get(column) or {})
    if column_overrides:
        col.update(column_overrides)
    if not col:
        return x
    out = dict(x)

    for total, lb_k, dr_k, shift_k, lb_name, dr_name in ROUTE_SPLIT_PAIRS:
        lb = col.get(lb_name)
        dr = col.get(dr_name)
        if lb is None and dr is None:
            continue
        tot = float(out[total])
        if lb is not None and dr is not None:
            out[lb_k] = tot * float(lb) / 100.0
            out[dr_k] = tot * float(dr) / 100.0
        elif lb is not None:
            out[lb_k] = tot * float(lb) / 100.0
            out[dr_k] = tot - out[lb_k]
        else:
            out[dr_k] = tot * float(dr) / 100.0
            out[lb_k] = tot - out[dr_k]
        out[shift_k] = float(out[dr_k])

    for label, feat in VCAP_LABELS.items():
        v = col.get(label)
        if v is not None:
            out[feat] = float(v)

    for label, feat in COUNT_LABELS.items():
        v = col.get(label)
        if v is not None:
            out[feat] = float(v)

    doc = col.get("Check timings for documentry and seal identity")
    phy = col.get("Check timings for physical")
    if doc is not None:
        out["ChkTime_Doc"] = float(out["ChkTime_Doc"]) * (1.0 + float(doc) / 100.0)
    if phy is not None:
        out["ChkTime_Phy"] = float(out["ChkTime_Phy"]) * (1.0 + float(phy) / 100.0)

    for label, feat in PCT_LABELS:
        v = col.get(label)
        if v is not None:
            out[feat] = _pct01(float(v))

    for key, val in col.items():
        if key.startswith("Percentage of inbound trucks stop due to pre-bording"):
            out["Pct_IB_PreBoard"] = _pct01(float(val))
        elif key.startswith("Percentage of outbound trucks stop due to pre-bording"):
            out["Pct_OB_PreBoard"] = _pct01(float(val))

    return out


def apply_dynamic_overrides(
    x: Dict[str, float],
    family: str,
    column: str,
    tables: Dict[str, Dict[str, Dict[str, float]]],
) -> Dict[str, float]:
    fam = tables.get(family) or {}
    col = fam.get(column) or {}
    if not col:
        return x
    out = dict(x)
    for feat, val in col.items():
        if feat in TRAINING_COLUMN_ORDER:
            out[feat] = float(val)
    return out
