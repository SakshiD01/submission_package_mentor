"""
Build AttributionSnapshot from pipeline JSON/CSV only (no PDFs).
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from llm_attribution.schema import (
    AttributionSnapshot,
    Interval90,
    MetricsBlock,
    ModellingContext,
    ResidualSummary,
    ShapFeature,
)


def _safe_filename(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", s)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_selected_model(
    target: str,
    selected_model: Optional[str],
    shap_dir: Path,
) -> str:
    if selected_model:
        return selected_model
    csv_path = shap_dir / "shap_selected_models.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Pass selected_model= or provide {csv_path} from run_step4_shap.py"
        )
    with csv_path.open(encoding="utf-8", newline="") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            if row.get("target") == target:
                return str(row["model"])
    raise KeyError(f"No row for target {target!r} in {csv_path}")


def _interval_for_model(conf_t: Dict[str, Any], model: str) -> Dict[str, Any]:
    if model not in conf_t:
        raise KeyError(f"Model {model!r} not in conformal_results for this target")
    return conf_t[model]


def assemble_attribution_snapshot(
    target: str,
    outputs_dir: Path,
    *,
    selected_model: Optional[str] = None,
    shap_top_k: int = 5,
    trained_dir: Optional[Path] = None,
) -> AttributionSnapshot:
    """
    Assemble snapshot from:
      outputs_dir/test_results.json
      outputs_dir/conformal_results.json
      outputs_dir/cv_results.json
      outputs_dir/step4_shap/{target}__{model}__importance.csv
      outputs_dir/step4_shap/shap_selected_models.csv (for model + policy if needed)
      trained_dir/split_meta.json (default outputs_dir/../trained_models or outputs_dir/trained_models)
    """
    od = outputs_dir.resolve()
    test_path = od / "test_results.json"
    conf_path = od / "conformal_results.json"
    cv_path = od / "cv_results.json"
    shap_dir = od / "step4_shap"

    for p in (test_path, conf_path, cv_path):
        if not p.is_file():
            raise FileNotFoundError(p)

    test = _load_json(test_path)
    conf = _load_json(conf_path)
    cv = _load_json(cv_path)

    if target not in test:
        raise KeyError(f"Target {target!r} not in test_results.json")

    model = _resolve_selected_model(target, selected_model, shap_dir)

    t_m = test[target][model]
    metrics = MetricsBlock(
        test_rmse=float(t_m["rmse"]),
        test_mae=float(t_m["mae"]),
        test_r2=float(t_m["r2"]),
        cv_mean_rmse=float(cv[target][model]["mean_rmse"]),
        cv_std_rmse=float(cv[target][model]["std_rmse"]),
    )

    conf_row = _interval_for_model(conf[target], model)
    half_w = float(conf_row["quantile"])
    full_w = float(conf_row["interval_width"])
    interval = Interval90(
        nominal_coverage=float(conf_row["coverage_level"]),
        half_width=half_w,
        full_width=full_w,
        empirical_coverage=float(conf_row["empirical_coverage"]),
        relative_rmse_to_best=float(conf_row["relative_rmse_to_best"]),
    )

    res = [float(x) for x in t_m["residuals"]]
    residual_summary = ResidualSummary(
        n_test=len(res),
        mean_abs_residual=float(sum(abs(x) for x in res) / len(res)) if res else 0.0,
        max_abs_residual=float(max((abs(x) for x in res), default=0.0)),
    )

    imp_path = shap_dir / f"{_safe_filename(target)}__{_safe_filename(model)}__importance.csv"
    top_shap: List[ShapFeature] = []
    if imp_path.is_file():
        rows: List[Dict[str, str]] = []
        with imp_path.open(encoding="utf-8", newline="") as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                rows.append(row)
        rows.sort(key=lambda r: float(r["mean_abs_shap"]), reverse=True)
        for i, row in enumerate(rows[: max(1, shap_top_k)], 1):
            top_shap.append(
                ShapFeature(
                    name=str(row["feature"]),
                    mean_abs_shap=float(row["mean_abs_shap"]),
                    rank=i,
                )
            )

    td = trained_dir or (od / "trained_models")
    sm_path = td / "split_meta.json"
    n_train, n_test = 103, 26
    if sm_path.is_file():
        meta = _load_json(sm_path)
        n_train = int(meta.get("n_train", n_train))
        n_test = int(meta.get("n_test", n_test))

    sel_policy = None
    shap_split = None
    sel_csv = shap_dir / "shap_selected_models.csv"
    if sel_csv.is_file():
        with sel_csv.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("target") == target:
                    sel_policy = str(row.get("selection_policy") or "") or None
                    shap_split = str(row.get("explain_split") or "") or None
                    break

    caveats = [
        "Surrogate trained on a NOLHC design (small n); SHAP reflects model dependence under that design, not guaranteed causal effects.",
        "Conformal-style intervals are computed on the hold-out test rows; interpret as descriptive uncertainty, not formal production guarantees.",
        "Composite model selection in the final report can include test RMSE; SHAP default selection composite_pre_test does not use hold-out labels.",
    ]

    modelling = ModellingContext(
        n_train=n_train,
        n_test=n_test,
        selection_policy=sel_policy,
        shap_explain_split=shap_split,
        note_composite_uses_test=True,
    )

    return AttributionSnapshot(
        target=target,
        selected_model=model,
        metrics=metrics,
        interval_90=interval,
        top_shap_features=top_shap,
        residual_summary=residual_summary,
        caveats=caveats,
        modelling_context=modelling,
    )
