#!/usr/bin/env python3
"""
Step 10: build pipeline_results.xlsx (spec §10).

Expects outputs from prior steps under experimenting_ml/outputs/.

Usage:
  python run_step10_report.py
  python run_step10_report.py --out outputs/pipeline_results.xlsx
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

from excel_report import build_ttest_structures, generate_excel_report, load_json  # noqa: E402
from training_columns import OUTPUT_COLUMN_ORDER  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Excel report (spec §10)")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "outputs",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Workbook path (default: <out-dir>/pipeline_results.xlsx)",
    )
    args = p.parse_args()

    out_dir = args.out_dir
    out_xlsx = args.out or (out_dir / "pipeline_results.xlsx")

    cv_path = out_dir / "cv_results.json"
    test_path = out_dir / "test_results.json"
    conf_path = out_dir / "conformal_results.json"
    pairs_path = out_dir / "paired_ttests_all_targets.csv"

    for req in (cv_path, test_path, conf_path, pairs_path):
        if not req.is_file():
            raise SystemExit(f"Missing required file: {req}")

    cv_results = load_json(cv_path)
    test_results = load_json(test_path)
    conformal_results = load_json(conf_path)

    status_paths = [
        out_dir / "cv_results.json",
        out_dir / "cv_fold_details.csv",
        out_dir / "paired_ttests_all_targets.csv",
        out_dir / "step2" / "friedman_nemenyi_summary.csv",
        out_dir / "experiment_master.xlsx",
        out_dir / "step3_pre_conformal",
        out_dir / "trained_models" / "split_meta.json",
        out_dir / "step4_shap" / "shap_selected_models.csv",
        out_dir / "shap_master.xlsx",
        out_dir / "test_results.json",
        out_dir / "pipeline_results.xlsx",
    ]
    experiment_status = {}
    for pth in status_paths:
        rel = str(pth.relative_to(out_dir.parent))
        experiment_status[rel] = pth.exists()

    sample_t = sorted(cv_results.keys())[0]
    model_names = sorted(cv_results[sample_t].keys())
    targets = [t for t in OUTPUT_COLUMN_ORDER if t in cv_results]

    ttest_by_target = build_ttest_structures(pairs_path, model_names, targets)

    generate_excel_report(
        cv_results=cv_results,
        test_results=test_results,
        conformal_results=conformal_results,
        ttest_by_target=ttest_by_target,
        targets=targets,
        model_names=model_names,
        output_path=out_xlsx,
        experiment_status=experiment_status,
    )
    print(f"Saved {out_xlsx}")


if __name__ == "__main__":
    main()
