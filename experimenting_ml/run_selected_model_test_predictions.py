#!/usr/bin/env python3
"""
After the experimental pipeline, export **held-out test** actuals vs predictions
using **only** the model chosen in Model_Selection (composite score in Excel).

The 26 test rows were never used for training or CV; they were used in Step 7 to
score all models. This file makes the “final model vs truth on holdout” table
explicit for the selected model per target.

Outputs:
  outputs/selected_model_test_predictions.csv  — long: one row per (target, test point)
  outputs/selected_model_test_summary.csv      — one row per target (RMSE/MAE/R² on test)

Usage:
  python run_selected_model_test_predictions.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

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
from models import get_models  # noqa: E402
from training_columns import OUTPUT_COLUMN_ORDER  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(
        description="Test actual vs predicted for Model_Selection winner only"
    )
    p.add_argument("--out-dir", type=Path, default=ROOT / "outputs")
    args = p.parse_args()
    od = args.out_dir

    cv_path = od / "cv_results.json"
    test_path = od / "test_results.json"
    conf_path = od / "conformal_results.json"
    pairs_path = od / "paired_ttests_all_targets.csv"
    meta_path = od / "trained_models" / "split_meta.json"

    for req in (cv_path, test_path, conf_path, pairs_path, meta_path):
        if not req.is_file():
            raise SystemExit(f"Missing {req}")

    cv_results = load_json(cv_path)
    test_results = load_json(test_path)
    conformal_results = load_json(conf_path)
    meta = load_json(meta_path)
    test_idx = meta["test_idx"]

    model_names = list(get_models().keys())
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

    X, Y = load_xy()
    if len(Y) != meta["n_total"]:
        raise SystemExit("Y length does not match split_meta n_total")

    long_rows = []
    summary_rows = []

    for _, row in selection_df.iterrows():
        target = row["Target"]
        model = row["Best_Model"]
        tr = test_results[target][model]
        y_act = Y.iloc[test_idx][target].to_numpy(dtype=float)
        y_pred = tr["y_pred"]
        res = tr["residuals"]
        for k, idx in enumerate(test_idx):
            long_rows.append(
                {
                    "dataset_row_index": int(idx),
                    "test_fold_position": k + 1,
                    "target": target,
                    "selected_model": model,
                    "y_actual": float(y_act[k]),
                    "y_predicted": float(y_pred[k]),
                    "residual": float(res[k]),
                }
            )
        summary_rows.append(
            {
                "target": target,
                "selected_model": model,
                "test_n": len(test_idx),
                "test_rmse": tr["rmse"],
                "test_mae": tr["mae"],
                "test_r2": tr["r2"],
            }
        )

    long_path = od / "selected_model_test_predictions.csv"
    with long_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "dataset_row_index",
                "test_fold_position",
                "target",
                "selected_model",
                "y_actual",
                "y_predicted",
                "residual",
            ],
        )
        w.writeheader()
        w.writerows(long_rows)

    sum_path = od / "selected_model_test_summary.csv"
    pd.DataFrame(summary_rows).to_csv(sum_path, index=False)

    print(f"Wrote {long_path} ({len(long_rows)} rows)")
    print(f"Wrote {sum_path}")


if __name__ == "__main__":
    main()
