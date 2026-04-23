#!/usr/bin/env python3
"""
Build one Excel workbook from Step 7/9 outputs: one sheet per target.

Reads:
  outputs/test_results.json
  outputs/conformal_results.json

Optional: embed residual plots from outputs/test_evaluation_final/plots/ if present.

Includes sheet ``Adaptive_Conformal_Selected``: same data as
``test_evaluation_final/selected_model_adaptive_conformal_from_step9.csv`` when that file exists;
otherwise computed from cv_results.json + paired t-tests + composite selection.

Usage:
  python run_step7_9_master_excel.py
  python run_step7_9_master_excel.py --out outputs/step7_9_test_conformal_master.xlsx
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
NOLHC_SRC = ROOT.parent / "nolhc_ml" / "src"
for pth in (SRC, NOLHC_SRC):
    if str(pth) not in sys.path:
        sys.path.insert(0, str(pth))

from step7_9_master_excel import build_step7_9_master_workbook  # noqa: E402
from training_columns import OUTPUT_COLUMN_ORDER  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Step 7/9 → one Excel workbook (one sheet per target)")
    p.add_argument("--out-dir", type=Path, default=ROOT / "outputs")
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Workbook path (default: <out-dir>/step7_9_test_conformal_master.xlsx)",
    )
    p.add_argument(
        "--plots-dir",
        type=Path,
        default=None,
        help="Optional: outputs/test_evaluation_final/plots for residual PNGs per target",
    )
    args = p.parse_args()

    out_dir = args.out_dir
    test_path = out_dir / "test_results.json"
    conf_path = out_dir / "conformal_results.json"
    for req in (test_path, conf_path):
        if not req.is_file():
            raise SystemExit(f"Missing {req}; run run_step7_9_evaluate.py first.")

    test_results = json.loads(test_path.read_text(encoding="utf-8"))
    conformal_results = json.loads(conf_path.read_text(encoding="utf-8"))

    sample_t = sorted(test_results.keys())[0]
    model_names = sorted(test_results[sample_t].keys())
    targets = [t for t in OUTPUT_COLUMN_ORDER if t in test_results]
    if not targets:
        targets = sorted(test_results.keys())

    out_xlsx = args.out or (out_dir / "step7_9_test_conformal_master.xlsx")
    plots_dir = args.plots_dir
    if plots_dir is None:
        default_plots = out_dir / "test_evaluation_final" / "plots"
        if default_plots.is_dir():
            plots_dir = default_plots

    build_step7_9_master_workbook(
        out_xlsx.resolve(),
        test_results=test_results,
        conformal_results=conformal_results,
        targets=targets,
        model_names=model_names,
        plots_dir=plots_dir,
        out_dir=out_dir.resolve(),
    )
    print(f"Wrote {out_xlsx.resolve()}")


if __name__ == "__main__":
    main()
