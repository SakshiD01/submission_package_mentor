#!/usr/bin/env python3
"""
Finalization step 2: Hold-out test evaluation package for reporting.

- Uses the **same** 20% hold-out as Step 7 (split_meta.json); no leakage.
- **Selected model per target** = Step 10 composite (CV + test + t-test + conformal inputs).
- **90% nominal** symmetric intervals: q = 90th percentile of |y − ŷ| on hold-out (reported explicitly).
- Exports long CSV (y, ŷ, residual, lower/upper at 90%), per-target summary, residual plots (QQ, hist, vs fitted).
- Writes ``TEST_EVAL_NARRATIVE.md`` (point error + interval width + residual flags in one place).

Prerequisites:
  python run_step7_9_evaluate.py
  (outputs: test_results.json, conformal_results.json, ...)

Usage:
  python run_test_set_evaluation_final.py
  python run_test_set_evaluation_final.py --nominal 0.90 --out-dir outputs/test_evaluation_final
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
NOLHC_SRC = ROOT.parent / "nolhc_ml" / "src"
for pth in (SRC, NOLHC_SRC):
    if str(pth) not in sys.path:
        sys.path.insert(0, str(pth))

from data import load_xy  # noqa: E402
from excel_report import (  # noqa: E402
    build_ttest_structures,
    compute_model_selection,
    load_json,
)
from holdout_conformal_report import (  # noqa: E402
    _safe_name,
    build_narrative_markdown,
    fixed_nominal_symmetric_intervals,
    plot_holdout_residual_panel,
    residual_diagnostic_flags,
)
from training_columns import OUTPUT_COLUMN_ORDER  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(
        description="Hold-out test report: 90% intervals + residual diagnostics for selected models"
    )
    p.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "test_evaluation_final")
    p.add_argument(
        "--nominal",
        type=float,
        default=0.90,
        help="Nominal coverage for symmetric |residual| quantile intervals (default 0.90)",
    )
    p.add_argument(
        "--project-root",
        type=Path,
        default=ROOT,
        help="For finding default outputs/",
    )
    p.add_argument("--parquet-dir", type=Path, default=None)
    p.add_argument("--xlsx", type=Path, default=None)
    args = p.parse_args()

    od = args.project_root / "outputs"
    cv_path = od / "cv_results.json"
    test_path = od / "test_results.json"
    conf_path = od / "conformal_results.json"
    pairs_path = od / "paired_ttests_all_targets.csv"
    meta_path = od / "trained_models" / "split_meta.json"

    for req in (cv_path, test_path, conf_path, pairs_path, meta_path):
        if not req.is_file():
            raise SystemExit(f"Missing {req}; run Step 7/9 and paired t-tests first.")

    cv_results = load_json(cv_path)
    test_results = load_json(test_path)
    conformal_results = load_json(conf_path)
    meta = load_json(meta_path)
    test_idx = meta["test_idx"]
    n_holdout = len(test_idx)

    sample_t = sorted(cv_results.keys())[0]
    model_names = sorted(cv_results[sample_t].keys())
    targets = [t for t in OUTPUT_COLUMN_ORDER if t in cv_results]

    ttest_by_target = build_ttest_structures(pairs_path, model_names, targets)
    selection_df = compute_model_selection(
        cv_results,
        test_results,
        conformal_results,
        ttest_by_target,
        targets,
        model_names,
    )

    X, Y = load_xy(parquet_dir=args.parquet_dir, xlsx_path=args.xlsx)
    if len(Y) != meta["n_total"]:
        raise SystemExit("Y length does not match split_meta n_total")

    nominal = float(args.nominal)
    if not 0.5 < nominal < 1.0:
        raise SystemExit("--nominal should be in (0.5, 1.0)")

    out_dir = args.out_dir
    if not out_dir.is_absolute():
        out_dir = (ROOT / out_dir).resolve()
    else:
        out_dir = out_dir.resolve()
    plots_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    long_rows = []
    summary_rows = []
    figure_paths: list[str] = []

    for _, row in selection_df.iterrows():
        target = str(row["Target"])
        model = str(row["Best_Model"])
        tr = test_results[target][model]
        y_act = Y.iloc[test_idx][target].to_numpy(dtype=float)
        y_pred = np.asarray(tr["y_pred"], dtype=float)
        if len(y_act) != len(y_pred):
            raise SystemExit(f"Length mismatch {target} {model}")

        interval = fixed_nominal_symmetric_intervals(y_act, y_pred, nominal=nominal)
        flags = residual_diagnostic_flags(interval["residuals"], y_act)

        png_path = plots_dir / f"{_safe_name(target)}_holdout_residual_diagnostics.png"
        plot_holdout_residual_panel(target, y_act, y_pred, png_path, nominal=nominal)
        try:
            rel_fig = str(png_path.relative_to(ROOT))
        except ValueError:
            rel_fig = str(png_path)

        for k, idx in enumerate(test_idx):
            long_rows.append(
                {
                    "dataset_row_index": int(idx),
                    "test_fold_position": k + 1,
                    "target": target,
                    "selected_model": model,
                    "y_actual": float(y_act[k]),
                    "y_predicted": float(y_pred[k]),
                    "residual": float(interval["residuals"][k]),
                    f"lower_{int(nominal * 100)}": float(interval["lower"][k]),
                    f"upper_{int(nominal * 100)}": float(interval["upper"][k]),
                    f"covered_{int(nominal * 100)}": bool(interval["covered"][k]),
                }
            )

        summary_rows.append(
            {
                "target": target,
                "selected_model": model,
                "test_n": n_holdout,
                "test_rmse": tr["rmse"],
                "test_mae": tr["mae"],
                "test_r2": tr["r2"],
                "nominal_coverage": nominal,
                "quantile_abs_residual": interval["quantile_abs_residual"],
                "interval_width_90": interval["interval_width"],
                "empirical_coverage_90": interval["empirical_coverage"],
                "mean_residual": flags["mean_residual"],
                "std_residual": flags["std_residual"],
                "skew_residual": flags["skew_residual"],
                "flag_systematic_bias": flags["flag_systematic_bias"],
                "flag_heavy_or_skewed_tails": flags["flag_heavy_or_skewed_tails"],
                "residual_plot_png": rel_fig,
            }
        )

    long_path = out_dir / "selected_holdout_predictions_long.csv"
    pd.DataFrame(long_rows).to_csv(long_path, index=False)

    sum_path = out_dir / "selected_holdout_summary.csv"
    pd.DataFrame(summary_rows).to_csv(sum_path, index=False)

    # Adaptive conformal (Step 9) snapshot for selected model only — for comparison
    adaptive_path = out_dir / "selected_model_adaptive_conformal_from_step9.csv"
    with adaptive_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "target",
                "selected_model",
                "adaptive_coverage_level",
                "empirical_coverage",
                "interval_width",
                "relative_rmse_to_best",
            ]
        )
        for t in targets:
            m = selection_df.loc[selection_df["Target"] == t, "Best_Model"].iloc[0]
            cr = conformal_results[t][m]
            w.writerow(
                [
                    t,
                    m,
                    cr["coverage_level"],
                    cr["empirical_coverage"],
                    cr["interval_width"],
                    cr.get("relative_rmse_to_best", ""),
                ]
            )

    out_rel = str(out_dir.relative_to(ROOT))
    figure_rels = [
        str(p.relative_to(ROOT)) for p in sorted(plots_dir.glob("*.png"))
    ]
    md = build_narrative_markdown(
        out_rel=out_rel,
        figures=figure_rels,
        summary_rows=summary_rows,
        n_holdout=n_holdout,
        nominal=nominal,
    )
    (out_dir / "TEST_EVAL_NARRATIVE.md").write_text(md, encoding="utf-8")

    meta_out = {
        "holdout_n": n_holdout,
        "nominal_coverage_reporting": nominal,
        "split_meta": str(meta_path),
        "outputs": {
            "long_predictions": str(long_path.relative_to(ROOT)),
            "summary": str(sum_path.relative_to(ROOT)),
            "narrative": str((out_dir / "TEST_EVAL_NARRATIVE.md").relative_to(ROOT)),
            "adaptive_conformal_selected": str(adaptive_path.relative_to(ROOT)),
        },
    }
    (out_dir / "test_evaluation_final.meta.json").write_text(
        json.dumps(meta_out, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote {long_path}")
    print(f"Wrote {sum_path}")
    print(f"Wrote {out_dir / 'TEST_EVAL_NARRATIVE.md'}")
    print(f"Wrote {adaptive_path}")
    print(f"Plots: {plots_dir}")


if __name__ == "__main__":
    main()
