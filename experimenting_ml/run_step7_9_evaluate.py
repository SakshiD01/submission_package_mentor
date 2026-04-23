#!/usr/bin/env python3
"""
Steps 7 & 9 (spec): test-set RMSE/MAE/R² + adaptive conformal summaries.

Reads split_meta.json and joblibs from outputs/trained_models/.

Usage:
  python run_step7_9_evaluate.py
  python run_step7_9_evaluate.py --trained-dir outputs/trained_models --out-dir outputs
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
NOLHC_SRC = ROOT.parent / "nolhc_ml" / "src"
for pth in (SRC, NOLHC_SRC):
    if str(pth) not in sys.path:
        sys.path.insert(0, str(pth))

from conformal_predict import compute_conformal_results  # noqa: E402
from data import load_xy  # noqa: E402
from training_columns import OUTPUT_COLUMN_ORDER  # noqa: E402
from test_eval import (  # noqa: E402
    compute_test_results,
    list_trained_model_names,
    load_split_meta,
    test_results_to_jsonable,
)


def main() -> None:
    p = argparse.ArgumentParser(description="Test evaluation + conformal (spec §7, §9)")
    p.add_argument("--parquet-dir", type=Path, default=None)
    p.add_argument("--xlsx", type=Path, default=None)
    p.add_argument(
        "--trained-dir",
        type=Path,
        default=ROOT / "outputs" / "trained_models",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "outputs",
    )
    args = p.parse_args()

    meta_path = args.trained_dir / "split_meta.json"
    if not meta_path.is_file():
        raise SystemExit(f"Missing {meta_path}; run run_step6_retrain.py first")

    meta = load_split_meta(meta_path)
    test_idx = meta["test_idx"]

    X, Y = load_xy(parquet_dir=args.parquet_dir, xlsx_path=args.xlsx)
    if len(X) != meta["n_total"]:
        raise SystemExit(
            f"Data rows {len(X)} != split_meta n_total {meta['n_total']}"
        )

    model_names = list_trained_model_names(args.trained_dir)
    if not model_names:
        raise SystemExit(
            f"No *.joblib under subfolders of {args.trained_dir}; run run_step6_retrain.py"
        )
    test_results = compute_test_results(
        X, Y, test_idx, args.trained_dir, model_names=model_names
    )

    y_test_by_target = {
        t: Y.iloc[test_idx][t].to_numpy(dtype=float)
        for t in Y.columns
    }

    conformal = compute_conformal_results(
        test_results, y_test_by_target, model_names=model_names
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)

    test_json = args.out_dir / "test_results.json"
    test_json.write_text(
        json.dumps(test_results_to_jsonable(test_results), indent=2),
        encoding="utf-8",
    )

    conf_json = args.out_dir / "conformal_results.json"
    conf_json.write_text(json.dumps(conformal, indent=2), encoding="utf-8")

    # Flat CSVs for spreadsheets
    targets = [c for c in OUTPUT_COLUMN_ORDER if c in test_results]

    test_csv = args.out_dir / "test_results.csv"
    with test_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["target", "model", "rmse", "mae", "r2"])
        for t in targets:
            for m in model_names:
                r = test_results[t][m]
                w.writerow([t, m, r["rmse"], r["mae"], r["r2"]])

    conf_csv = args.out_dir / "conformal_results.csv"
    with conf_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "target",
                "model",
                "coverage_level",
                "relative_rmse_to_best",
                "quantile",
                "empirical_coverage",
                "interval_width",
            ]
        )
        for t in targets:
            for m in model_names:
                r = conformal[t][m]
                w.writerow(
                    [
                        t,
                        m,
                        r["coverage_level"],
                        r["relative_rmse_to_best"],
                        r["quantile"],
                        r["empirical_coverage"],
                        r["interval_width"],
                    ]
                )

    print(f"Wrote {test_json}")
    print(f"Wrote {test_csv}")
    print(f"Wrote {conf_json}")
    print(f"Wrote {conf_csv}")
    print(f"Test rows: {len(test_idx)}")


if __name__ == "__main__":
    main()
