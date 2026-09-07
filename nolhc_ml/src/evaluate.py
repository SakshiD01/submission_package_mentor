"""
Per-KPI evaluation report for the NOLHC ML surrogate.

Computes, for every output slug in ``models/<version>/registry.json``:
    1. Training (in-sample) RMSE / MAE / R^2.
    2. Hold-out test (single 80/20 split, ``random_state=42``)
       RMSE / MAE / R^2 — fresh clone fit on the 80%, evaluated on the 20%.
    3. 5-fold cross-validation RMSE / MAE / R^2 — per-fold values plus
       mean ± std and the OOF-pooled metric. Same KFold seed as training
       (``shuffle=True, random_state=42``).
    4. Residual analysis on the OOF predictions: mean, std, abs-mean,
       min/max, and the q05 / q50 / q95 quantiles. A CSV with one row per
       training run (``y_true``, ``y_pred_oof``, ``residual``) is written to
       ``models/<version>/residuals/<slug>.csv`` so the paper can render
       custom plots.
    5. 90 % prediction interval:
         • marginal split-conformal half-width from the OOF |residuals|
           with the standard (n+1)/n correction; and
         • for GPR-registered KPIs, the native Gaussian interval
           ``±1.645·σ̂(x)`` summarised by median/mean σ̂.

Outputs:
    models/<version>/evaluation.json            machine-readable
    models/<version>/evaluation_report.md       paper-ready Markdown tables
    models/<version>/residuals/<slug>.csv       OOF residuals per KPI
    models/<version>/plots/<slug>_residuals.png plot (if matplotlib available)

Run:
    python -m evaluate                 # uses models/v1, processed parquet
    python -m evaluate --version v1
    python -m evaluate --xlsx data/raw/nolhc_runs.xlsx
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.ensemble import StackingRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, train_test_split

from candidate_models import CANDIDATE_MODELS
from data_loader import (
    DEFAULT_XLSX,
    PROJECT_ROOT,
    load_data,
    load_parquet_pair,
)
from training_columns import TRAINING_COLUMN_ORDER

ALPHA_PI: float = 0.10            # 90% prediction interval
N_SPLITS_CV: int = 5
RANDOM_STATE: int = 42
TEST_SIZE: float = 0.20
Z_90: float = 1.6448536269514722  # one-sided z for 90% Gaussian PI

warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(math.sqrt(mean_squared_error(y_true, y_pred)))


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    return {
        "rmse": _rmse(y_true, y_pred),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def _rebuild_estimator(registered_as: str, base_learners: List[str]) -> BaseEstimator:
    """Recreate the *un-fit* architecture used at training time."""
    if registered_as == "stacking":
        if len(base_learners) < 2:
            raise ValueError("Stacking requires >=2 base learners")
        ests = [(n, clone(CANDIDATE_MODELS[n])) for n in base_learners]
        return StackingRegressor(
            estimators=ests,
            final_estimator=Ridge(alpha=1.0),
            cv=5,
            passthrough=False,
            n_jobs=-1,
        )
    if registered_as not in CANDIDATE_MODELS:
        raise KeyError(f"Unknown registered_as: {registered_as!r}")
    return clone(CANDIDATE_MODELS[registered_as])


def _conformal_half_width(abs_resid: np.ndarray, alpha: float) -> float:
    """
    Split-conformal half-width using the OOF |residuals| as the calibration
    sample. Uses the standard finite-sample (n+1)/n quantile correction:

        q* = quantile(|resid|, ceil((1-α)(n+1))/n)
    """
    n = len(abs_resid)
    if n == 0:
        return float("nan")
    k = int(math.ceil((1.0 - alpha) * (n + 1)))
    k = min(max(k, 1), n)
    sorted_abs = np.sort(abs_resid)
    return float(sorted_abs[k - 1])


def _residual_stats(resid: np.ndarray) -> Dict[str, float]:
    return {
        "mean": float(np.mean(resid)),
        "std": float(np.std(resid, ddof=1)) if len(resid) > 1 else 0.0,
        "abs_mean": float(np.mean(np.abs(resid))),
        "min": float(np.min(resid)),
        "max": float(np.max(resid)),
        "q05": float(np.quantile(resid, 0.05)),
        "q50": float(np.quantile(resid, 0.50)),
        "q95": float(np.quantile(resid, 0.95)),
    }


def evaluate(
    version: str = "v1",
    *,
    xlsx_path: Optional[Path] = None,
    use_parquet: bool = True,
    make_plots: bool = True,
) -> Dict[str, Any]:
    model_dir = PROJECT_ROOT / "models" / version
    if not model_dir.is_dir():
        raise FileNotFoundError(f"Missing model directory: {model_dir}")

    with open(model_dir / "registry.json", encoding="utf-8") as f:
        registry: Dict[str, Any] = json.load(f)

    scaler = joblib.load(model_dir / "scaler_X.pkl")

    if use_parquet and (PROJECT_ROOT / "data" / "processed" / "X_train.parquet").is_file():
        x_df, y_df = load_parquet_pair()
    else:
        x_df, y_df, _ = load_data(xlsx_path or DEFAULT_XLSX, save=False)

    missing = [c for c in TRAINING_COLUMN_ORDER if c not in x_df.columns]
    if missing:
        raise ValueError(f"Training-column mismatch: missing {missing[:10]}")

    X_raw = x_df[TRAINING_COLUMN_ORDER].to_numpy(dtype=np.float64)
    X_scaled = scaler.transform(X_raw)
    n = X_scaled.shape[0]

    idx_train, idx_test = train_test_split(
        np.arange(n), test_size=TEST_SIZE, random_state=RANDOM_STATE
    )
    Xtr, Xte = X_scaled[idx_train], X_scaled[idx_test]

    kf = KFold(n_splits=N_SPLITS_CV, shuffle=True, random_state=RANDOM_STATE)

    have_mpl = False
    plots_dir = model_dir / "plots"
    if make_plots:
        try:
            import matplotlib  # noqa: F401

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt  # noqa: F401

            have_mpl = True
            plots_dir.mkdir(exist_ok=True)
        except ImportError:
            have_mpl = False

    residuals_dir = model_dir / "residuals"
    residuals_dir.mkdir(exist_ok=True)

    report: Dict[str, Any] = {
        "version": version,
        "n_total": n,
        "n_train": len(idx_train),
        "n_test": len(idx_test),
        "n_splits_cv": N_SPLITS_CV,
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "alpha_prediction_interval": ALPHA_PI,
        "coverage_target": 1.0 - ALPHA_PI,
        "n_outputs": len(registry.get("outputs", {})),
        "outputs": {},
    }

    print(
        f"[evaluate] version={version} n={n} (train={len(idx_train)} test={len(idx_test)}) "
        f"cv={N_SPLITS_CV}-fold seed={RANDOM_STATE}"
    )

    for i, (slug, info) in enumerate(registry.get("outputs", {}).items(), start=1):
        raw_key = info.get("raw_key", slug)
        if raw_key not in y_df.columns:
            print(f"  [{i:>2}] {slug}: skip — {raw_key!r} not in Y columns")
            continue

        y = y_df[raw_key].to_numpy(dtype=np.float64)
        ytr, yte = y[idx_train], y[idx_test]

        registered_as: str = info["registered_as"]
        base_learners: List[str] = info.get("stack_base_learners") or []

        # ---- 1) training in-sample (use already-fit registered model) ----
        fitted = joblib.load(model_dir / f"model_{slug}.pkl")
        train_metrics = _metrics(y, fitted.predict(X_scaled))

        # ---- 2) held-out test (fresh clone on 80% → predict 20%) ----
        try:
            est_test = _rebuild_estimator(registered_as, base_learners)
            est_test.fit(Xtr, ytr)
            test_metrics: Dict[str, Any] = _metrics(yte, est_test.predict(Xte))
        except Exception as exc:  # noqa: BLE001
            test_metrics = {"error": str(exc)[:160]}

        # ---- 3) 5-fold CV (manual loop to reuse OOF preds for §4 / §5) ----
        per_fold: List[Dict[str, float]] = []
        oof = np.zeros_like(y, dtype=np.float64)
        oof_gpr_std: Optional[np.ndarray] = (
            np.zeros_like(y, dtype=np.float64)
            if registered_as in ("gpr_rbf", "gpr_matern")
            else None
        )
        fold_ok = True
        for tr_i, te_i in kf.split(X_scaled):
            try:
                est = _rebuild_estimator(registered_as, base_learners)
                est.fit(X_scaled[tr_i], y[tr_i])
                if oof_gpr_std is not None and isinstance(est, GaussianProcessRegressor):
                    yp, std_te = est.predict(X_scaled[te_i], return_std=True)
                    oof_gpr_std[te_i] = std_te
                else:
                    yp = est.predict(X_scaled[te_i])
            except Exception as exc:  # noqa: BLE001
                fold_ok = False
                per_fold.append({"error": str(exc)[:160]})
                oof[te_i] = np.nan
                if oof_gpr_std is not None:
                    oof_gpr_std[te_i] = np.nan
                continue
            oof[te_i] = yp
            per_fold.append(_metrics(y[te_i], yp))

        if fold_ok:
            cv_summary = {
                "rmse_mean": float(np.mean([f["rmse"] for f in per_fold])),
                "rmse_std": float(np.std([f["rmse"] for f in per_fold])),
                "mae_mean": float(np.mean([f["mae"] for f in per_fold])),
                "mae_std": float(np.std([f["mae"] for f in per_fold])),
                "r2_mean": float(np.mean([f["r2"] for f in per_fold])),
                "r2_std": float(np.std([f["r2"] for f in per_fold])),
                "pooled_oof": _metrics(y, oof),
                "per_fold": per_fold,
            }
        else:
            cv_summary = {"per_fold": per_fold, "error": "one or more folds failed"}

        # ---- 4) residual analysis (OOF) ----
        if fold_ok:
            resid = y - oof
            residuals = _residual_stats(resid)
            pd.DataFrame(
                {
                    "row": np.arange(n),
                    "y_true": y,
                    "y_pred_oof": oof,
                    "residual": resid,
                }
            ).to_csv(residuals_dir / f"{slug}.csv", index=False)
        else:
            resid = None
            residuals = {"error": "OOF unavailable"}

        # ---- 5) prediction intervals ----
        if resid is not None:
            pi = {
                "method": "split_conformal_oof_residuals",
                "alpha": ALPHA_PI,
                "coverage_target": 1.0 - ALPHA_PI,
                "half_width": _conformal_half_width(np.abs(resid), ALPHA_PI),
                "n_calibration": int(len(resid)),
            }
        else:
            pi = {"method": "split_conformal_oof_residuals", "error": "OOF unavailable"}

        gpr_native: Optional[Dict[str, Any]] = None
        if registered_as in ("gpr_rbf", "gpr_matern"):
            try:
                if oof_gpr_std is not None and fold_ok:
                    std_oof = oof_gpr_std
                    coverage = float(
                        np.mean(np.abs(resid) <= Z_90 * std_oof)
                    ) if resid is not None else float("nan")
                    gpr_native = {
                        "scope": "out_of_fold",
                        "z_90pct": Z_90,
                        "median_std": float(np.median(std_oof)),
                        "mean_std": float(np.mean(std_oof)),
                        "median_half_width": float(Z_90 * np.median(std_oof)),
                        "mean_half_width": float(Z_90 * np.mean(std_oof)),
                        "empirical_coverage_oof_90pct": coverage,
                    }
                elif isinstance(fitted, GaussianProcessRegressor):
                    _, std = fitted.predict(X_scaled, return_std=True)
                    gpr_native = {
                        "scope": "fitted_on_training_points_zero_by_design",
                        "z_90pct": Z_90,
                        "median_std": float(np.median(std)),
                        "mean_std": float(np.mean(std)),
                        "median_half_width": float(Z_90 * np.median(std)),
                        "mean_half_width": float(Z_90 * np.mean(std)),
                    }
            except Exception as exc:  # noqa: BLE001
                gpr_native = {"error": str(exc)[:160]}

        # ---- record ----
        report["outputs"][slug] = {
            "raw_key": raw_key,
            "unit": info.get("unit", ""),
            "registered_as": registered_as,
            "train_in_sample": train_metrics,
            "test_holdout": test_metrics,
            "cv": cv_summary,
            "residuals_oof": residuals,
            "prediction_interval_90pct": pi,
            "gpr_native_interval_90pct": gpr_native,
        }

        # ---- plot ----
        if have_mpl and resid is not None:
            import matplotlib.pyplot as plt

            fig, axs = plt.subplots(1, 2, figsize=(10, 4))
            axs[0].scatter(y, oof, s=16, alpha=0.75, edgecolor="none")
            lo = float(min(y.min(), oof.min()))
            hi = float(max(y.max(), oof.max()))
            axs[0].plot([lo, hi], [lo, hi], "k--", lw=1)
            axs[0].set_xlabel("Actual")
            axs[0].set_ylabel("OOF predicted")
            axs[0].set_title(f"{raw_key}: pred vs. actual (OOF)")
            axs[1].scatter(oof, resid, s=16, alpha=0.75, edgecolor="none")
            axs[1].axhline(0.0, color="k", lw=1)
            axs[1].set_xlabel("OOF predicted")
            axs[1].set_ylabel("Residual = y − ŷ")
            axs[1].set_title("Residuals")
            fig.suptitle(
                f"{raw_key} — {registered_as}  ·  "
                f"train R²={train_metrics['r2']:.3f}  ·  "
                f"CV R²={cv_summary['r2_mean']:.3f}±{cv_summary['r2_std']:.3f}",
                fontsize=10,
            )
            fig.tight_layout()
            fig.savefig(plots_dir / f"{slug}_residuals.png", dpi=130)
            plt.close(fig)

        tr_r2 = train_metrics["r2"]
        cv_r2 = cv_summary.get("r2_mean", float("nan"))
        te_r2 = test_metrics.get("r2", float("nan")) if isinstance(test_metrics, dict) else float("nan")
        print(
            f"  [{i:>2}/{report['n_outputs']}] {slug:<22} {registered_as:<14} "
            f"train R²={tr_r2:.3f}  test R²={te_r2:.3f}  cv R²={cv_r2:.3f}"
        )

    with open(model_dir / "evaluation.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    _write_markdown_report(report, model_dir / "evaluation_report.md")

    print(
        f"\n[evaluate] wrote:\n"
        f"  {model_dir / 'evaluation.json'}\n"
        f"  {model_dir / 'evaluation_report.md'}\n"
        f"  {residuals_dir}/<slug>.csv\n"
        + (f"  {plots_dir}/<slug>_residuals.png\n" if have_mpl else "")
    )
    return report


def _fmt(v: Any, ndigits: int = 3) -> str:
    if v is None or isinstance(v, str):
        return "—"
    try:
        if math.isnan(float(v)):
            return "—"
    except (TypeError, ValueError):
        return "—"
    return f"{float(v):.{ndigits}f}"


def _write_markdown_report(report: Dict[str, Any], path: Path) -> None:
    coverage_pct = int(round((1.0 - report["alpha_prediction_interval"]) * 100))
    lines: List[str] = []
    lines.append("# NOLHC ML surrogate — per-KPI evaluation\n")
    lines.append(
        f"Model version **{report['version']}** · "
        f"training runs **{report['n_total']}** · "
        f"holdout split **{report['n_train']}/{report['n_test']}** · "
        f"CV **{report['n_splits_cv']}-fold** (seed={report['random_state']}) · "
        f"prediction intervals **{coverage_pct}%** (split-conformal on OOF residuals).\n"
    )
    lines.append(
        "> *Training* = registered model refit on the **full** dataset, evaluated on the same data (apparent error). "
        "*Test* = fresh model clone refit on the 80% training split, evaluated on the 20% holdout. "
        "*CV* = 5-fold mean ± std across folds; ‘pooled OOF’ stitches the five held-out folds back together.\n"
    )

    lines.append("\n## 1. Headline metrics per KPI\n")
    lines.append(
        "| # | KPI | Unit | Registered model | Train RMSE | Train MAE | Train R² | "
        "Test RMSE | Test MAE | Test R² | CV RMSE (mean ± std) | CV MAE (mean ± std) | "
        "CV R² (mean ± std) | 90% PI half-width |"
    )
    lines.append(
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    for i, (slug, o) in enumerate(report["outputs"].items(), start=1):
        tr = o["train_in_sample"]
        te = o["test_holdout"]
        cv = o["cv"]
        pi = o["prediction_interval_90pct"]
        if "error" in te:
            te_row = ("—", "—", "—")
        else:
            te_row = (_fmt(te["rmse"]), _fmt(te["mae"]), _fmt(te["r2"]))
        if "error" in cv:
            cv_row = ("—", "—", "—")
        else:
            cv_row = (
                f"{_fmt(cv['rmse_mean'])} ± {_fmt(cv['rmse_std'])}",
                f"{_fmt(cv['mae_mean'])} ± {_fmt(cv['mae_std'])}",
                f"{_fmt(cv['r2_mean'])} ± {_fmt(cv['r2_std'])}",
            )
        lines.append(
            "| "
            + " | ".join(
                [
                    str(i),
                    slug,
                    o["unit"],
                    o["registered_as"],
                    _fmt(tr["rmse"]),
                    _fmt(tr["mae"]),
                    _fmt(tr["r2"]),
                    *te_row,
                    *cv_row,
                    _fmt(pi.get("half_width")) if "half_width" in pi else "—",
                ]
            )
            + " |"
        )

    lines.append("\n## 2. Residual analysis (out-of-fold)\n")
    lines.append(
        "| # | KPI | resid mean | resid std | |resid| mean | q05 | q50 | q95 | min | max |"
    )
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for i, (slug, o) in enumerate(report["outputs"].items(), start=1):
        r = o["residuals_oof"]
        if "error" in r:
            lines.append(f"| {i} | {slug} | — | — | — | — | — | — | — | — |")
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    str(i),
                    slug,
                    _fmt(r["mean"]),
                    _fmt(r["std"]),
                    _fmt(r["abs_mean"]),
                    _fmt(r["q05"]),
                    _fmt(r["q50"]),
                    _fmt(r["q95"]),
                    _fmt(r["min"]),
                    _fmt(r["max"]),
                ]
            )
            + " |"
        )

    gpr_rows = [
        (slug, o["gpr_native_interval_90pct"])
        for slug, o in report["outputs"].items()
        if o.get("gpr_native_interval_90pct") and "error" not in o["gpr_native_interval_90pct"]
    ]
    if gpr_rows:
        lines.append("\n## 3. GPR-native 90% interval (Gaussian, out-of-fold σ̂)\n")
        lines.append(
            "| KPI | median σ̂ (OOF) | mean σ̂ (OOF) | median half-width (1.645·σ̂) | mean half-width | empirical coverage |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|")
        for slug, g in gpr_rows:
            lines.append(
                "| "
                + " | ".join(
                    [
                        slug,
                        _fmt(g["median_std"]),
                        _fmt(g["mean_std"]),
                        _fmt(g["median_half_width"]),
                        _fmt(g["mean_half_width"]),
                        _fmt(g.get("empirical_coverage_oof_90pct")),
                    ]
                )
                + " |"
            )

    lines.append("\n## 4. Per-fold CV (R²)\n")
    fold_hdr = "| KPI | " + " | ".join([f"fold {k+1}" for k in range(report["n_splits_cv"])]) + " | mean | std |"
    sep = "|---|" + "---:|" * (report["n_splits_cv"] + 2)
    lines.append(fold_hdr)
    lines.append(sep)
    for slug, o in report["outputs"].items():
        cv = o["cv"]
        per_fold = cv.get("per_fold", [])
        cells: List[str] = []
        for k in range(report["n_splits_cv"]):
            if k < len(per_fold) and "error" not in per_fold[k]:
                cells.append(_fmt(per_fold[k]["r2"]))
            else:
                cells.append("—")
        cells.append(_fmt(cv.get("r2_mean")))
        cells.append(_fmt(cv.get("r2_std")))
        lines.append("| " + slug + " | " + " | ".join(cells) + " |")

    lines.append(
        "\n## Methodology notes\n\n"
        "- **RMSE / MAE** are reported in the KPI's native unit (hours for travel/wait "
        "times, fractions for utilisation). **R²** is unitless.\n"
        "- **Train / Test / CV split.** All three views share the same `KFold("
        f"{report['n_splits_cv']}, shuffle=True, random_state={report['random_state']})` "
        "seed used during training. The 80/20 holdout uses the same seed.\n"
        "- **Prediction intervals.** Marginal 90% intervals are built by split-conformal "
        "calibration on out-of-fold residuals: half-width = "
        f"quantile(|y − ŷ_OOF|, ⌈{coverage_pct/100:.2f}·(n+1)⌉/n). "
        "Coverage is guaranteed in distribution under exchangeability.\n"
        "- **GPR-native intervals** are reported for KPIs whose registered model is "
        "`gpr_rbf` or `gpr_matern`: σ̂(x) is the GP posterior std and the 90% interval "
        "is ±1.6449·σ̂(x). We summarise σ̂ with its median and mean over the training set.\n"
        "- **Residual analysis.** All residuals are OOF (y − ŷ from 5-fold CV) — the "
        "honest residuals an operator would see on a new run with the same data-generating "
        "process. Per-row residuals are persisted to "
        "`residuals/<slug>.csv` for downstream plotting.\n"
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--version", default="v1", help="model version directory under models/")
    p.add_argument("--xlsx", type=Path, default=None,
                   help="override source workbook (defaults to data/processed parquet)")
    p.add_argument("--no-plots", action="store_true", help="skip matplotlib plots")
    args = p.parse_args(argv)

    evaluate(
        version=args.version,
        xlsx_path=args.xlsx,
        use_parquet=args.xlsx is None,
        make_plots=not args.no_plots,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
