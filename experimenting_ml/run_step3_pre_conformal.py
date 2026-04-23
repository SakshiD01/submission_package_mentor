#!/usr/bin/env python3
"""
Step 3 — before conformal / final test reporting:

  (a) Explicit per-target CV winner table (each target ranked independently).
  (b) Baselines: add via ``python run_baselines_cv.py`` then ``run_paired_ttests.py``.
  (c) OOF calibration metrics + plots for top-K models per target (pooled CV folds).
  (d) HP sensitivity from ``cv_fold_details.csv`` if Step 1 used ``--save-fold-details``.

Next pipeline steps when satisfied: ``run_step6_retrain.py`` → ``run_step7_9_evaluate.py``.

Usage:
  python run_step3_pre_conformal.py
  python run_step3_pre_conformal.py --top-k 3 --skip-hp
  python run_step3_pre_conformal.py --master-xlsx outputs/step3_report.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data import load_xy  # noqa: E402
from splits import train_test_indices  # noqa: E402
from step2_cv_config import infer_cv_config  # noqa: E402
from step2_residuals import collect_cv_residuals_long  # noqa: E402
from step3_calibration import calibration_for_top_models  # noqa: E402
from step3_hp_sensitivity import run_hp_sensitivity_all  # noqa: E402
from step3_master_excel import build_step3_workbook  # noqa: E402
from step3_selection import export_per_target_selection_table, load_cv  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Step 3 — pre-conformal checks")
    p.add_argument("--cv-json", type=Path, default=ROOT / "outputs" / "cv_results.json")
    p.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "step3")
    p.add_argument("--top-k", type=int, default=3, help="Top models per target for calibration & HP plots")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--parquet-dir", type=Path, default=None)
    p.add_argument("--xlsx", type=Path, default=None)
    p.add_argument(
        "--residuals-long",
        type=Path,
        default=None,
        help="Reuse Step 2 cv_residuals_long.csv if present; else refit OOF for top-K only",
    )
    p.add_argument(
        "--fold-details",
        type=Path,
        default=ROOT / "outputs" / "cv_fold_details.csv",
    )
    p.add_argument("--skip-calibration", action="store_true")
    p.add_argument("--skip-hp", action="store_true")
    p.add_argument(
        "--master-xlsx",
        type=Path,
        default=None,
        help="After Step 3, write one workbook (one sheet per target) with tables + PNGs.",
    )
    args = p.parse_args()

    if not args.cv_json.is_file():
        raise SystemExit(f"Missing {args.cv_json}")

    cv_results = load_cv(args.cv_json)
    targets = sorted(cv_results.keys())
    model_names = sorted(cv_results[targets[0]].keys())
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    sel = export_per_target_selection_table(
        args.cv_json, model_names, top_k=args.top_k
    )
    sel_path = out / "per_target_cv_selection.csv"
    sel.to_csv(sel_path, index=False)
    print(f"Wrote {sel_path}")

    readme = out / "STEP3_README.txt"
    readme.write_text(
        "\n".join(
            [
                "Step 3 — pre-conformal methodology",
                "",
                "(a) Per-target selection: see per_target_cv_selection.csv (best = min mean CV RMSE per target).",
                "    Excel Step 10 composite selection remains separate (CV + test + t-test wins).",
                "",
                "(b) Baselines: DummyRegressor(mean) and LinearRegression are in get_models() as",
                "    Baseline_Mean and Baseline_OLS. Merge CV with: python run_baselines_cv.py",
                "    then: python run_paired_ttests.py",
                "",
                "(c) Calibration: OOF pooled y vs ŷ; check mean_residual ~ 0 and slope_y_on_yhat ~ 1.",
                "    Plots in calibration/ subdirectory.",
                "",
                "(d) HP sensitivity: requires cv_fold_details.csv from run_step1_cv.py --save-fold-details.",
                "",
                "Then: run_step6_retrain.py → run_step7_9_evaluate.py (conformal).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {readme}")

    if not args.skip_calibration:
        res_path = args.residuals_long or (
            ROOT / "outputs" / "step2" / "cv_residuals_long.csv"
        )
        if res_path.is_file():
            res_df = pd.read_csv(res_path)
            need = {"target", "model", "y_true", "y_pred"}
            if not need.issubset(res_df.columns):
                raise SystemExit(f"{res_path} missing columns {need}")
        else:
            print(
                "Building OOF residual table for top-K models only (no cv_residuals_long.csv)…",
                flush=True,
            )
            X, Y = load_xy(parquet_dir=args.parquet_dir, xlsx_path=args.xlsx)
            n = len(X)
            train_idx, _ = train_test_indices(n, seed=args.seed, train_frac=0.8)
            X_train = X.iloc[train_idx].reset_index(drop=True).to_numpy(dtype=float)
            n_splits, n_repeats, _ = infer_cv_config(cv_results)
            rows = []
            for t in targets:
                tops = [
                    m
                    for m, _ in sorted(
                        [
                            (m, cv_results[t][m]["mean_rmse"])
                            for m in model_names
                        ],
                        key=lambda x: x[1],
                    )[: max(1, args.top_k)]
                ]
                y_train = (
                    Y.iloc[train_idx].reset_index(drop=True)[t].to_numpy(dtype=float)
                )
                rows.extend(
                    collect_cv_residuals_long(
                        X_train,
                        y_train,
                        cv_results,
                        t,
                        tops,
                        n_splits=n_splits,
                        n_repeats=n_repeats,
                        random_state=args.seed,
                    )
                )
            res_df = pd.DataFrame(rows)

        cal_dir = out / "calibration"
        cal_df = calibration_for_top_models(
            res_df,
            cv_results,
            targets=targets,
            model_names=model_names,
            out_dir=cal_dir,
            top_k=args.top_k,
        )
        cal_csv = out / "calibration_cv_metrics.csv"
        cal_df.to_csv(cal_csv, index=False)
        print(f"Wrote {cal_csv} and figures under {cal_dir}/")

    if not args.skip_hp:
        hp_dir = out / "hp_sensitivity"
        hp_log = run_hp_sensitivity_all(
            args.cv_json,
            args.fold_details,
            model_names,
            targets,
            hp_dir,
            top_k=args.top_k,
        )
        hp_csv = out / "hp_sensitivity_run_log.csv"
        hp_log.to_csv(hp_csv, index=False)
        print(f"Wrote {hp_csv} and plots under {hp_dir}/")

    if args.master_xlsx is not None:
        build_step3_workbook(args.master_xlsx.resolve(), out.resolve())
        print(f"Wrote Step 3 master workbook {args.master_xlsx.resolve()}")


if __name__ == "__main__":
    main()
