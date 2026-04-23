#!/usr/bin/env python3
"""
Rebuild ``experiment_master.xlsx`` from existing Step 2 artifacts (no re-CV, no re-Friedman).

Requires:
  outputs/cv_results.json
  outputs/step2/friedman_nemenyi_summary.csv
  outputs/step2/friedman_nemenyi_meta.json
  outputs/step2/nemenyi_pvalues/<target>.csv
  outputs/step2/cd_per_target/<target>.png
  outputs/step2/learning_curves/grid__<target>.png  (from --learning-curves-all-models)
  optional: outputs/step2/residual_plots/grid_residuals__<target>.png

Usage:
  python run_build_master_excel.py --out outputs/experiment_master.xlsx
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from step2_master_excel import build_master_workbook  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Build master Excel from saved Step 2 outputs")
    p.add_argument(
        "--cv-json",
        type=Path,
        default=ROOT / "outputs" / "cv_results.json",
    )
    p.add_argument(
        "--step2-dir",
        type=Path,
        default=ROOT / "outputs" / "step2",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "outputs" / "experiment_master.xlsx",
    )
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--test-results-csv", type=Path, default=None)
    p.add_argument("--target", type=str, default=None)
    args = p.parse_args()

    cv_path = args.cv_json
    if not cv_path.is_file():
        raise SystemExit(f"Missing {cv_path}")

    summary_path = args.step2_dir / "friedman_nemenyi_summary.csv"
    meta_path = args.step2_dir / "friedman_nemenyi_meta.json"
    if not summary_path.is_file() or not meta_path.is_file():
        raise SystemExit(
            f"Missing {summary_path} or {meta_path}; run run_mentor_step2.py first."
        )

    cv_results = json.loads(cv_path.read_text(encoding="utf-8"))
    targets = sorted(cv_results.keys())
    if args.target:
        if args.target not in cv_results:
            raise SystemExit(f"Unknown target {args.target!r}")
        targets = [args.target]

    model_names = sorted(cv_results[targets[0]].keys())
    summary_df = pd.read_csv(summary_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    nemenyi_by_target = {}
    for t in targets:
        npth = args.step2_dir / "nemenyi_pvalues" / f"{t}.csv"
        if npth.is_file():
            nemenyi_by_target[t] = pd.read_csv(npth, index_col=0)

    test_csv = args.test_results_csv
    if test_csv is None:
        cand = ROOT / "outputs" / "test_results.csv"
        test_csv = cand if cand.is_file() else None

    build_master_workbook(
        args.out.resolve(),
        cv_path=cv_path.resolve(),
        cv_results=cv_results,
        targets=targets,
        model_names=model_names,
        step2_dir=args.step2_dir.resolve(),
        summary_df=summary_df,
        nemenyi_by_target=nemenyi_by_target,
        meta=meta,
        alpha=args.alpha,
        test_results_csv=test_csv,
    )
    print(f"Wrote {args.out.resolve()}")


if __name__ == "__main__":
    main()
