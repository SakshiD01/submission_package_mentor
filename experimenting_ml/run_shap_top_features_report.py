#!/usr/bin/env python3
"""
XAI attribution layer — join SHAP importance CSVs with domain crosswalk.

Reads:
  outputs/step4_shap/*__importance.csv (paired with shap_selected_models.csv by default)
  docs/nolhc_inputs_crosswalk.csv

Writes:
  outputs/step4_shap/xai_review/xai_shap_top_features_long.csv
  outputs/step4_shap/xai_review/xai_shap_domain_review.xlsx

Use the long CSV / Excel to validate top features against domain knowledge before
stakeholder-facing text (fill flags in the crosswalk CSV as needed).

Usage:
  python run_shap_top_features_report.py
  python run_shap_top_features_report.py --top-k 5 --shap-dir outputs/step4_shap
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
NOLHC_SRC = ROOT.parent / "nolhc_ml" / "src"
for pth in (SRC, NOLHC_SRC):
    if str(pth) not in sys.path:
        sys.path.insert(0, str(pth))

from shap_crosswalk_report import (  # noqa: E402
    build_shap_review_long_table,
    write_shap_xai_review_artifacts,
)


def main() -> None:
    p = argparse.ArgumentParser(
        description="SHAP top features + domain crosswalk for XAI review"
    )
    p.add_argument(
        "--shap-dir",
        type=Path,
        default=ROOT / "outputs" / "step4_shap",
    )
    p.add_argument(
        "--crosswalk",
        type=Path,
        default=ROOT.parent / "docs" / "nolhc_inputs_crosswalk.csv",
    )
    p.add_argument(
        "--selected-models",
        type=Path,
        default=None,
        help="Defaults to <shap-dir>/shap_selected_models.csv if present",
    )
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Default: <shap-dir>/xai_review",
    )
    args = p.parse_args()

    shap_dir = args.shap_dir
    sel = args.selected_models or (shap_dir / "shap_selected_models.csv")
    if not args.crosswalk.is_file():
        raise SystemExit(f"Missing crosswalk: {args.crosswalk}")

    long_df = build_shap_review_long_table(
        shap_dir.resolve(),
        args.crosswalk.resolve(),
        top_k=max(1, int(args.top_k)),
        selected_models_csv=sel if sel.is_file() else None,
    )

    out_dir = args.out_dir or (shap_dir / "xai_review")
    if not out_dir.is_absolute():
        out_dir = (ROOT / out_dir).resolve()
    else:
        out_dir = out_dir.resolve()

    xlsx = write_shap_xai_review_artifacts(out_dir, long_df)
    print(f"Wrote {out_dir / 'xai_shap_top_features_long.csv'}")
    if xlsx:
        print(f"Wrote {xlsx}")
    else:
        print("(openpyxl not installed — CSV only)")
    print(f"Rows: {len(long_df)}")


if __name__ == "__main__":
    main()
