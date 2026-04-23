#!/usr/bin/env python3
"""
Build one Excel workbook with **one sheet per target** from Step 4 SHAP outputs.

Each sheet contains:
  - model, selection_policy, explain_split
  - table: feature, mean_abs_shap (from ``*__importance.csv``)
  - embedded PNGs: summary bar, beeswarm, waterfall_row* (when present)

Requires:
  outputs/step4_shap/shap_selected_models.csv (from run_step4_shap.py)
  matching ``<target>__<model>__*`` files in the same folder

Usage:
  python run_step4_shap_master_excel.py
  python run_step4_shap_master_excel.py --shap-dir outputs/step4_shap --out outputs/shap_master.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from step4_shap_master_excel import build_shap_master_workbook  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Combine SHAP outputs into one Excel workbook")
    p.add_argument(
        "--shap-dir",
        type=Path,
        default=ROOT / "outputs" / "step4_shap",
        help="Directory with shap_selected_models.csv and per-target SHAP artifacts",
    )
    p.add_argument(
        "--selected-csv",
        type=Path,
        default=None,
        help="Defaults to <shap-dir>/shap_selected_models.csv",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "outputs" / "shap_master.xlsx",
        help="Output workbook path",
    )
    p.add_argument(
        "--max-image-width",
        type=int,
        default=720,
        help="Max width in pixels when embedding PNGs (Pillow scales if installed)",
    )
    args = p.parse_args()

    shap_dir = args.shap_dir
    selected = args.selected_csv or (shap_dir / "shap_selected_models.csv")
    if not selected.is_file():
        raise SystemExit(f"Missing {selected}; run run_step4_shap.py first.")
    build_shap_master_workbook(
        args.out,
        shap_dir=shap_dir,
        selected_csv=selected,
        max_width_px=args.max_image_width,
    )
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
