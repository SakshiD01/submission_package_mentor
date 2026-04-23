#!/usr/bin/env python3
"""
Step 6 (spec §6): refit all models on the full 80% training split using
best_params from cv_results.json. Saves scaler + one joblib per target/model.

Prior CV must use the same split seed (default 42) as this script.

Usage:
  python run_step6_retrain.py
  python run_step6_retrain.py --cv outputs/cv_results.json --out-dir outputs/trained_models
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data import load_xy  # noqa: E402
from retrain import (  # noqa: E402
    fit_full_training_models,
    load_cv_results,
    save_trained_bundle,
)
from splits import train_test_indices  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Final training on full train set (spec §6)")
    p.add_argument("--parquet-dir", type=Path, default=None)
    p.add_argument("--xlsx", type=Path, default=None)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--cv",
        type=Path,
        default=ROOT / "outputs" / "cv_results.json",
        help="CV results with best_params per target/model",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "outputs" / "trained_models",
        help="Directory for scaler.joblib and per-target model joblibs",
    )
    p.add_argument(
        "--models",
        nargs="*",
        default=None,
        help="Subset of model names (default: all keys present in cv_results.json)",
    )
    args = p.parse_args()

    if not args.cv.is_file():
        raise SystemExit(f"Missing {args.cv}; run run_step1_cv.py first")

    X, Y = load_xy(parquet_dir=args.parquet_dir, xlsx_path=args.xlsx)
    n = len(X)
    train_idx, test_idx = train_test_indices(n, seed=args.seed, train_frac=0.8)

    X_train = X.iloc[train_idx].reset_index(drop=True)
    Y_train = Y.iloc[train_idx].reset_index(drop=True)

    cv_results = load_cv_results(args.cv)
    missing = [c for c in Y.columns if c not in cv_results]
    if missing:
        raise SystemExit(f"cv_results missing targets: {missing[:5]}")

    sample_t = sorted(cv_results.keys())[0]
    mnames = sorted(cv_results[sample_t].keys())
    if args.models:
        want = set(args.models)
        mnames = [m for m in mnames if m in want]
        if not mnames:
            raise SystemExit("No models left after --models filter")

    scaler, trained = fit_full_training_models(
        X_train, Y_train, cv_results, model_names=mnames
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "seed": args.seed,
        "n_total": int(n),
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "train_idx": train_idx.tolist(),
        "test_idx": test_idx.tolist(),
        "cv_results_path": str(args.cv.resolve()),
    }
    (args.out_dir / "split_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    paths = save_trained_bundle(scaler, trained, args.out_dir)
    print(f"Train rows: {len(X_train)}; wrote {len(paths)} artifacts under {args.out_dir}")


if __name__ == "__main__":
    main()
