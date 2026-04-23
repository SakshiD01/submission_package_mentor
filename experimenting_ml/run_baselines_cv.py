#!/usr/bin/env python3
"""
CV for baseline models only (mean predictor + OLS), then merge into existing cv_results.json.

Use when your main ``cv_results.json`` was built without baselines. Reuses the same
train split and CV scheme as inferred from the existing JSON.

Usage:
  python run_baselines_cv.py
  python run_baselines_cv.py --cv outputs/cv_results.json --out outputs/cv_results.json
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

from cross_validation import run_cv_all  # noqa: E402
from data import load_xy  # noqa: E402
from models import get_models  # noqa: E402
from splits import train_test_indices  # noqa: E402
from step2_cv_config import infer_cv_config  # noqa: E402


def _json_safe(obj):
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return float(obj) if isinstance(obj, np.floating) else int(obj)
    if obj is None or isinstance(obj, (str, bool, int, float)):
        return obj
    if isinstance(obj, tuple):
        return list(obj)
    return str(obj)


def main() -> None:
    p = argparse.ArgumentParser(description="Append baseline CV to cv_results.json")
    p.add_argument("--cv", type=Path, default=ROOT / "outputs" / "cv_results.json")
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Default: overwrite --cv",
    )
    p.add_argument("--parquet-dir", type=Path, default=None)
    p.add_argument("--xlsx", type=Path, default=None)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    out = args.out or args.cv
    if not args.cv.is_file():
        raise SystemExit(f"Missing {args.cv}")

    existing = json.loads(args.cv.read_text(encoding="utf-8"))
    n_splits, n_repeats, _ = infer_cv_config(existing)

    baseline_names = ["Baseline_Mean", "Baseline_OLS"]
    for b in baseline_names:
        if b not in get_models():
            raise SystemExit(f"Model {b!r} missing from get_models()")

    X, Y = load_xy(parquet_dir=args.parquet_dir, xlsx_path=args.xlsx)
    n = len(X)
    train_idx, _ = train_test_indices(n, seed=args.seed, train_frac=0.8)
    X_train = X.iloc[train_idx].reset_index(drop=True)
    Y_train = Y.iloc[train_idx].reset_index(drop=True)

    cv_b = run_cv_all(
        X_train,
        Y_train,
        model_names=baseline_names,
        n_splits=n_splits,
        n_repeats=n_repeats,
        random_state=args.seed,
    )

    merged = dict(existing)
    for target in cv_b:
        if target not in merged:
            merged[target] = {}
        for m in baseline_names:
            merged[target][m] = cv_b[target][m]

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(_json_safe(merged), indent=2), encoding="utf-8")
    print(
        f"Merged {baseline_names} into {out} "
        f"({n_splits}-fold × {n_repeats} repeats). "
        f"Re-run run_paired_ttests.py and downstream steps."
    )


if __name__ == "__main__":
    main()
