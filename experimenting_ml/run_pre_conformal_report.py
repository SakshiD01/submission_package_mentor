#!/usr/bin/env python3
"""
Build one checkpoint workbook for mentor approval before conformal/final testing.

Usage:
  python run_pre_conformal_report.py
  python run_pre_conformal_report.py --out outputs/pre_conformal_checkpoint.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pre_conformal_report import build_pre_conformal_workbook  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(
        description="Create one pre-conformal workbook with mentor-step evidence"
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "outputs",
        help="Directory containing CV/step2/step3/step4 outputs",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "outputs" / "pre_conformal_checkpoint.xlsx",
        help="Output workbook path",
    )
    p.add_argument(
        "--shap-top-n",
        type=int,
        default=10,
        help="Top SHAP features per target to include in SHAP_Top_Features sheet",
    )
    args = p.parse_args()

    build_pre_conformal_workbook(
        out_dir=args.out_dir.resolve(),
        output_path=args.out.resolve(),
        shap_top_n=max(1, int(args.shap_top_n)),
    )
    print(f"Wrote {args.out.resolve()}")


if __name__ == "__main__":
    main()

