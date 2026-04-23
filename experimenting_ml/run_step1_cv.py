#!/usr/bin/env python3
"""
Step 1: CV hyperparameter search on 80% training data for all targets × models.
Writes outputs/cv_results.json (+ optional summary CSV).

CV modes:
  repeated10 (default) — RepeatedKFold 10-fold × n_repeats (default 3) for stabler estimates on n≈103.
  kfold5 — legacy shuffled 5-fold (single pass), as in the original spec draft.

Usage (from repo root or experimenting_ml/):
  python run_step1_cv.py
  python run_step1_cv.py --cv-mode repeated10 --n-repeats 5
  python run_step1_cv.py --cv-mode kfold5
  python run_step1_cv.py --target TT_OB_Agri --models Ridge Lasso
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cross_validation import run_cv_all, run_cv_all_with_details  # noqa: E402
from data import DEFAULT_PARQUET_DIR, DEFAULT_XLSX, load_xy  # noqa: E402
from splits import train_test_indices  # noqa: E402


def _json_safe(obj):
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    if isinstance(obj, float):
        return float(obj)
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, tuple):
        return list(obj)
    return str(obj)


def main() -> None:
    p = argparse.ArgumentParser(description="CV hyperparameter search (train split only)")
    p.add_argument(
        "--parquet-dir",
        type=Path,
        default=None,
        help=f"Directory with X_train.parquet / Y_train.parquet (default: {DEFAULT_PARQUET_DIR})",
    )
    p.add_argument("--xlsx", type=Path, default=None, help="Load from xlsx instead of parquet")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--target", type=str, default=None, help="Single target column (default: all 20)")
    p.add_argument("--models", nargs="*", default=None, help="Subset of model names")
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "outputs" / "cv_results.json",
        help="JSON output path",
    )
    p.add_argument(
        "--save-fold-details",
        action="store_true",
        help="Also save per-parameter per-fold CV metrics (RMSE/MAE) to CSV/XLSX.",
    )
    p.add_argument(
        "--cv-mode",
        choices=("repeated10", "kfold5"),
        default="repeated10",
        help="repeated10: 10-fold × n_repeats (default 3). kfold5: single shuffled 5-fold.",
    )
    p.add_argument(
        "--n-repeats",
        type=int,
        default=3,
        help="RepeatedKFold repeat count when --cv-mode repeated10 (mentor: 3 or 5).",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-model progress (default prints each target/model as it finishes).",
    )
    args = p.parse_args()

    if args.cv_mode == "kfold5":
        n_splits, n_repeats = 5, 1
    else:
        n_splits, n_repeats = 10, max(1, int(args.n_repeats))

    if not args.quiet:
        print("Loading X/Y …", flush=True)

    X, Y = load_xy(parquet_dir=args.parquet_dir, xlsx_path=args.xlsx)

    n = len(X)
    train_idx, _test_idx = train_test_indices(n, seed=args.seed, train_frac=0.8)

    X_train = X.iloc[train_idx].reset_index(drop=True)
    Y_train = Y.iloc[train_idx].reset_index(drop=True)

    target_names = [args.target] if args.target else None
    if args.target and args.target not in Y.columns:
        raise SystemExit(f"Unknown target {args.target!r}. Columns: {list(Y.columns)}")

    if args.save_fold_details:
        cv_results, detail_rows = run_cv_all_with_details(
            X_train,
            Y_train,
            target_names=target_names,
            model_names=args.models,
            n_splits=n_splits,
            n_repeats=n_repeats,
            random_state=args.seed,
            verbose=not args.quiet,
        )
    else:
        cv_results = run_cv_all(
            X_train,
            Y_train,
            target_names=target_names,
            model_names=args.models,
            n_splits=n_splits,
            n_repeats=n_repeats,
            random_state=args.seed,
            verbose=not args.quiet,
        )
        detail_rows = []

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(_json_safe(cv_results), f, indent=2)

    # Long-form summary for quick inspection
    rows = []
    for t, per_m in cv_results.items():
        for m, r in per_m.items():
            rows.append(
                {
                    "target": t,
                    "model": m,
                    "mean_rmse": r["mean_rmse"],
                    "std_rmse": r["std_rmse"],
                    "cv_n_splits": r.get("cv_n_splits", n_splits),
                    "cv_n_repeats": r.get("cv_n_repeats", n_repeats),
                    "cv_n_scores": r.get("cv_n_scores", len(r.get("fold_rmses", []))),
                    "best_params": json.dumps(r["best_params"], sort_keys=True),
                }
            )
    summary_path = args.out.with_suffix(".summary.csv")
    pd.DataFrame(rows).sort_values(["target", "mean_rmse"]).to_csv(
        summary_path, index=False
    )

    if args.save_fold_details:
        details_df = pd.DataFrame(detail_rows)
        details_df["cv_mode"] = args.cv_mode
        details_df["cv_n_splits"] = n_splits
        details_df["cv_n_repeats"] = n_repeats
        details_df["cv_n_scores_expected"] = n_splits * n_repeats
        details_df["cv_seed"] = args.seed
        details_df["params"] = details_df["params"].apply(
            lambda d: json.dumps(d, sort_keys=True)
        )
        details_df["fold_order"] = details_df["fold"].apply(
            lambda f: 999 if f == "aggregate" else int(f)
        )
        details_df = details_df.sort_values(
            ["target", "model", "param_index", "fold_order"]
        ).drop(columns=["fold_order"])
        details_csv = args.out.with_name("cv_fold_details.csv")
        details_xlsx = args.out.with_name("cv_fold_details.xlsx")
        details_df.to_csv(details_csv, index=False)
        details_df.to_excel(details_xlsx, index=False)

    print(f"Wrote {args.out}")
    print(f"Wrote {summary_path}")
    if args.save_fold_details:
        print(f"Wrote {details_csv}")
        print(f"Wrote {details_xlsx}")
    print(
        f"Train rows: {len(X_train)} / {n} total (80% split, seed={args.seed}); "
        f"CV: {n_splits}-fold × {n_repeats} repeat(s) → {n_splits * n_repeats} val scores per HP set"
    )


if __name__ == "__main__":
    main()
