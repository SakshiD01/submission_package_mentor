#!/usr/bin/env python3
"""
Build paired t-test table from CV fold RMSEs (spec §8).

Writes one CSV: all targets × C(19,2) = 171 pairs per target = 3420 rows (default).

Usage:
  python run_paired_ttests.py
  python run_paired_ttests.py --cv outputs/cv_results.json --out outputs/paired_ttests_all_targets.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from paired_ttests import run_paired_ttests  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Paired t-tests on CV fold RMSEs")
    p.add_argument(
        "--cv",
        type=Path,
        default=ROOT / "outputs" / "cv_results.json",
        help="cv_results.json from run_step1_cv.py",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "outputs" / "paired_ttests_all_targets.csv",
        help="Output CSV path",
    )
    p.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Significance threshold for Significant column",
    )
    args = p.parse_args()

    if not args.cv.is_file():
        raise SystemExit(f"Missing CV file: {args.cv}")

    cv_results = json.loads(args.cv.read_text(encoding="utf-8"))
    rows = run_paired_ttests(cv_results, alpha=args.alpha)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "target",
        "Model_A",
        "Model_B",
        "Mean_RMSE_A",
        "Mean_RMSE_B",
        "t_stat",
        "p_value",
        "Significant",
        "Better_Model",
    ]
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print(f"Wrote {args.out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
