#!/usr/bin/env python3
"""
Build one Excel workbook from Step 3 outputs (one sheet per target).

Requires ``outputs/step3/per_target_cv_selection.csv`` and optionally calibration /
HP sensitivity artifacts from ``run_step3_pre_conformal.py``.

Usage:
  python run_step3_master_excel.py
  python run_step3_master_excel.py --step3-dir outputs/step3 --out outputs/step3_report.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from step3_master_excel import build_step3_workbook  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Step 3 → single Excel (one sheet per target)")
    p.add_argument(
        "--step3-dir",
        type=Path,
        default=ROOT / "outputs" / "step3",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "outputs" / "step3_report.xlsx",
    )
    args = p.parse_args()

    build_step3_workbook(args.out.resolve(), args.step3_dir.resolve())
    print(f"Wrote {args.out.resolve()}")


if __name__ == "__main__":
    main()
