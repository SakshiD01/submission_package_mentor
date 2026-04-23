#!/usr/bin/env python3
"""
Mentor Step 2: Friedman + Nemenyi, CD diagrams, learning curves, CV residual tables/plots.

Reads ``outputs/cv_results.json`` (aligned ``fold_rmses`` per model per target).
Friedman/Nemenyi use those out-of-fold RMSEs (training pool only), not the 26-row test set.

Usage (from ``experimenting_ml/``):
  python run_mentor_step2.py
  python run_mentor_step2.py --target TT_OB_Agri --shortlist-k 4
  python run_mentor_step2.py --skip-learning-curves --skip-residuals

  Full report (all models learning-curve grid + master Excel, one sheet per target):
  python run_mentor_step2.py --learning-curves-all-models \\
      --master-xlsx outputs/experiment_master.xlsx
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

from data import DEFAULT_PARQUET_DIR, DEFAULT_XLSX, load_xy  # noqa: E402
from splits import train_test_indices  # noqa: E402
from step2_cd_plot import plot_cd_cross_target_mean_rank, plot_cd_diagram  # noqa: E402
from step2_cv_config import infer_cv_config  # noqa: E402
from step2_learning_curves import (  # noqa: E402
    plot_learning_curves_grid_all_models,
    plot_learning_curves_shortlist,
)
from step2_master_excel import build_master_workbook  # noqa: E402
from step2_ranking import (  # noqa: E402
    build_fold_rmse_matrix,
    run_ranking_for_all_targets,
    shortlist_by_median_mean_rank,
)
from step2_residuals import (  # noqa: E402
    collect_cv_residuals_long,
    plot_residual_boxplots_grid_all_models,
    summarize_residuals_by_fold,
)


def main() -> None:
    p = argparse.ArgumentParser(description="Mentor Step 2 — ranking, CD, curves, residuals")
    p.add_argument(
        "--cv-json",
        type=Path,
        default=ROOT / "outputs" / "cv_results.json",
        help="CV results from run_step1_cv.py",
    )
    p.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "step2")
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--target", type=str, default=None, help="Single target (default: all)")
    p.add_argument("--shortlist-k", type=int, default=5, help="Learning-curve / residual plot shortlist size")
    p.add_argument("--n-splits", type=int, default=None, help="Override CV splits (must match Step 1)")
    p.add_argument("--n-repeats", type=int, default=None, help="Override CV repeats (must match Step 1)")
    p.add_argument("--parquet-dir", type=Path, default=None)
    p.add_argument("--xlsx", type=Path, default=None)
    p.add_argument("--skip-learning-curves", action="store_true")
    p.add_argument("--skip-residuals", action="store_true")
    p.add_argument("--skip-plots", action="store_true")
    p.add_argument(
        "--learning-curves-all-models",
        action="store_true",
        help="Per target: one PNG grid of learning curves for every model (slow).",
    )
    p.add_argument(
        "--master-xlsx",
        type=Path,
        default=None,
        help="Write one workbook with one sheet per target (tables + embedded CD/LC/residual PNGs).",
    )
    p.add_argument(
        "--test-results-csv",
        type=Path,
        default=None,
        help="Optional columns target,model,rmse,mae,r2 merged into each sheet (default: outputs/test_results.csv if present).",
    )
    args = p.parse_args()

    if args.learning_curves_all_models and (
        args.skip_learning_curves or args.skip_plots
    ):
        raise SystemExit(
            "--learning-curves-all-models requires learning curves and plots "
            "(do not pass --skip-learning-curves or --skip-plots)."
        )

    cv_path = args.cv_json
    if not cv_path.is_file():
        raise SystemExit(f"Missing {cv_path}")

    cv_results = json.loads(cv_path.read_text(encoding="utf-8"))
    targets = sorted(cv_results.keys())
    if args.target:
        if args.target not in cv_results:
            raise SystemExit(f"Unknown target {args.target!r}")
        targets = [args.target]

    first_models = list(cv_results[targets[0]].keys())
    model_names = sorted(first_models)

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    n_splits, n_repeats, n_scores = infer_cv_config(cv_results)
    if args.n_splits is not None:
        n_splits = args.n_splits
    if args.n_repeats is not None:
        n_repeats = args.n_repeats
    if n_splits * n_repeats != n_scores:
        raise SystemExit(
            f"--n-splits × --n-repeats ({n_splits}×{n_repeats}) must equal "
            f"len(fold_rmses)={n_scores} in {cv_path}"
        )

    summary_df, nemenyi_by_target, meta = run_ranking_for_all_targets(
        cv_path,
        model_names,
        targets,
        alpha=args.alpha,
    )
    summary_path = out / "friedman_nemenyi_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    n_dir = out / "nemenyi_pvalues"
    n_dir.mkdir(parents=True, exist_ok=True)
    for t, df_nm in nemenyi_by_target.items():
        df_nm.to_csv(n_dir / f"{t}.csv")

    meta_path = out / "friedman_nemenyi_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    matrices_by_target = {}
    if not args.skip_plots:
        cd_dir = out / "cd_per_target"
        cd_dir.mkdir(parents=True, exist_ok=True)
        for t in targets:
            mat = build_fold_rmse_matrix(cv_results, t, model_names)
            matrices_by_target[t] = mat
            plot_cd_diagram(
                mat,
                cd_dir / f"{t}.png",
                title=f"CD diagram — {t} (N={len(mat)} CV scores)",
                alpha=args.alpha,
            )
        plot_cd_cross_target_mean_rank(
            matrices_by_target,
            model_names,
            out / "cd_cross_target_mean_rank.png",
            alpha=args.alpha,
        )

    shortlist = shortlist_by_median_mean_rank(
        cv_path, model_names, targets, k=args.shortlist_k
    )

    run_learning = not args.skip_learning_curves and not args.skip_plots
    run_residuals = not args.skip_residuals
    if run_learning or run_residuals:
        X, Y = load_xy(parquet_dir=args.parquet_dir, xlsx_path=args.xlsx)
        n = len(X)
        train_idx, _ = train_test_indices(n, seed=args.seed, train_frac=0.8)
        X_train = X.iloc[train_idx].reset_index(drop=True).to_numpy(dtype=float)
    else:
        X = Y = None
        train_idx = None
        X_train = None

    if run_learning:
        lc_root = out / "learning_curves"
        for t in targets:
            y_train = Y.iloc[train_idx].reset_index(drop=True)[t].to_numpy(dtype=float)
            if args.learning_curves_all_models:
                plot_learning_curves_grid_all_models(
                    X_train,
                    y_train,
                    cv_results,
                    t,
                    model_names,
                    lc_root / f"grid__{t}.png",
                )
            else:
                plot_learning_curves_shortlist(
                    X_train,
                    y_train,
                    cv_results,
                    t,
                    shortlist,
                    lc_root,
                )

    if run_residuals:
        assert X is not None and Y is not None and train_idx is not None
        res_rows = []
        for t in targets:
            y_train = Y.iloc[train_idx].reset_index(drop=True)[t].to_numpy(dtype=float)
            res_rows.extend(
                collect_cv_residuals_long(
                    X_train,
                    y_train,
                    cv_results,
                    t,
                    model_names,
                    n_splits=n_splits,
                    n_repeats=n_repeats,
                    random_state=args.seed,
                )
            )
        res_df = pd.DataFrame(res_rows)
        res_csv = out / "cv_residuals_long.csv"
        res_df.to_csv(res_csv, index=False)
        summ = summarize_residuals_by_fold(res_df)
        summ.to_csv(out / "cv_residuals_fold_summary.csv", index=False)

        if not args.skip_plots:
            rplot_dir = out / "residual_plots"
            for t in targets:
                plot_residual_boxplots_grid_all_models(
                    res_df,
                    t,
                    model_names,
                    rplot_dir / f"grid_residuals__{t}.png",
                )

    print(f"Wrote {summary_path}")
    print(f"Wrote Nemenyi tables under {n_dir}/")
    print(f"Shortlist (median rank): {shortlist}")
    print(f"CV scheme (for residuals): {n_splits}-fold × {n_repeats} → {n_splits * n_repeats} scores")
    if run_residuals:
        print(f"Wrote {out / 'cv_residuals_long.csv'}")

    if (
        args.master_xlsx is not None
        and run_learning
        and not args.learning_curves_all_models
    ):
        print(
            "Note: --master-xlsx looks for learning_curves/grid__<target>.png. "
            "Use --learning-curves-all-models to generate full-model grids (shortlist-only PNGs use a different filename).",
            flush=True,
        )

    if args.master_xlsx is not None:
        test_csv = args.test_results_csv
        if test_csv is None:
            cand = ROOT / "outputs" / "test_results.csv"
            test_csv = cand if cand.is_file() else None
        build_master_workbook(
            args.master_xlsx.resolve(),
            cv_path=cv_path.resolve(),
            cv_results=cv_results,
            targets=targets,
            model_names=model_names,
            step2_dir=out.resolve(),
            summary_df=summary_df,
            nemenyi_by_target=nemenyi_by_target,
            meta=meta,
            alpha=args.alpha,
            test_results_csv=test_csv,
        )
        print(f"Wrote master workbook {args.master_xlsx.resolve()}")


if __name__ == "__main__":
    main()
