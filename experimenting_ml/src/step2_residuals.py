"""
Mentor Step 2d: CV residuals (out-of-fold) using best_params from cv_results.json.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import KFold, RepeatedKFold
from sklearn.preprocessing import StandardScaler

from models import NEEDS_SCALING, get_models
from step2_cv_config import infer_cv_config


def _make_splitter(
    n_splits: int, n_repeats: int, random_state: int
):
    if n_repeats <= 1:
        return KFold(
            n_splits=n_splits, shuffle=True, random_state=random_state
        ), n_splits
    return RepeatedKFold(
        n_splits=n_splits, n_repeats=n_repeats, random_state=random_state
    ), n_splits * n_repeats


def collect_cv_residuals_long(
    X_train: np.ndarray,
    y_train: np.ndarray,
    cv_results: Dict[str, Any],
    target: str,
    model_names: Sequence[str],
    *,
    n_splits: Optional[int] = None,
    n_repeats: Optional[int] = None,
    random_state: int = 42,
) -> List[Dict[str, Any]]:
    """
    For each model, refit with best_params on the same CV splits as Step 1
    (same sklearn random_state) and record one row per validation observation.
    """
    if n_splits is None or n_repeats is None:
        inf_ns, inf_nr, _ = infer_cv_config(cv_results)
        n_splits = n_splits if n_splits is not None else inf_ns
        n_repeats = n_repeats if n_repeats is not None else inf_nr

    splitter, n_expected = _make_splitter(n_splits, n_repeats, random_state)
    models_cfg = get_models()
    rows: List[Dict[str, Any]] = []

    for mname in model_names:
        cfg = models_cfg[mname]
        bp = cv_results[target][mname]["best_params"]
        needs_scale = mname in NEEDS_SCALING
        est = clone(cfg["model"])
        est.set_params(**bp)

        fold_idx = 0
        for train_idx, val_idx in splitter.split(X_train):
            fold_idx += 1
            X_tr, X_va = X_train[train_idx], X_train[val_idx]
            y_tr, y_va = y_train[train_idx], y_train[val_idx]

            if needs_scale:
                scaler = StandardScaler()
                X_tr_f = scaler.fit_transform(X_tr)
                X_va_f = scaler.transform(X_va)
            else:
                X_tr_f, X_va_f = X_tr, X_va

            est_f = clone(est)
            est_f.fit(X_tr_f, y_tr)
            pred = est_f.predict(X_va_f)

            for j in range(len(val_idx)):
                ri = int(val_idx[j])
                yt = float(y_va[j])
                pr = float(pred[j])
                rows.append(
                    {
                        "target": target,
                        "model": mname,
                        "fold": fold_idx,
                        "train_row_index": ri,
                        "y_true": yt,
                        "y_pred": pr,
                        "residual": yt - pr,
                    }
                )

        if fold_idx != n_expected:
            raise RuntimeError(
                f"{target}/{mname}: expected {n_expected} folds, got {fold_idx}"
            )

    return rows


def summarize_residuals_by_fold(df: pd.DataFrame) -> pd.DataFrame:
    """Per target, model, fold: std / skew of residuals (heteroscedasticity hint)."""
    g = df.groupby(["target", "model", "fold"], sort=False)["residual"]
    out = g.agg(["count", "mean", "std", "min", "max"]).reset_index()
    # sample skew (no scipy dependency for core path)
    def _skew(x: pd.Series) -> float:
        x = x.dropna().to_numpy(dtype=float)
        if len(x) < 3:
            return float("nan")
        m = x.mean()
        s = x.std(ddof=1)
        if s == 0:
            return 0.0
        return float(((x - m) ** 3).mean() / (s**3))

    skew_rows = []
    for key, sub in df.groupby(["target", "model", "fold"], sort=False):
        skew_rows.append(
            {"target": key[0], "model": key[1], "fold": key[2], "skew": _skew(sub["residual"])}
        )
    sk = pd.DataFrame(skew_rows)
    return out.merge(sk, on=["target", "model", "fold"], how="left")


def plot_residual_boxplots_by_fold(
    df: pd.DataFrame,
    target: str,
    models: Sequence[str],
    out_path: Path,
    *,
    figsize_per_model: float = 3.2,
) -> None:
    """One row of boxplots: per model, residual distribution by CV fold."""
    sub = df[(df["target"] == target) & (df["model"].isin(models))]
    if sub.empty:
        return
    n = len(models)
    fig, axes = plt.subplots(
        1,
        n,
        figsize=(figsize_per_model * max(n, 1), 4),
        sharey=True,
        squeeze=False,
    )
    axr = axes[0]
    for ax, m in zip(axr, models):
        d = sub[sub["model"] == m]
        folds = sorted(d["fold"].unique())
        data = [d.loc[d["fold"] == f, "residual"].to_numpy(dtype=float) for f in folds]
        ax.boxplot(data, showmeans=True)
        ax.set_xticks(np.arange(1, len(folds) + 1))
        ax.set_xticklabels([str(f) for f in folds])
        ax.axhline(0.0, color="black", linewidth=0.6, linestyle="--")
        ax.set_title(m, fontsize=9)
        ax.set_xlabel("Fold")
        ax.tick_params(axis="x", labelsize=7)
    axr[0].set_ylabel("Residual (y − ŷ)")
    fig.suptitle(f"CV residuals by fold — {target}", fontsize=11)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_residual_boxplots_grid_all_models(
    df: pd.DataFrame,
    target: str,
    model_names: Sequence[str],
    out_path: Path,
    *,
    ncols: int = 4,
    dpi: int = 115,
) -> None:
    """
    One figure per target: each model gets a small boxplot of CV residuals by fold.
    ``sharey=False`` so different residual scales per model remain visible.
    """
    sub = df[df["target"] == target]
    n = len(model_names)
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(2.7 * ncols, 2.15 * nrows), squeeze=False
    )
    for idx, m in enumerate(model_names):
        r, c = divmod(idx, ncols)
        ax = axes[r][c]
        d = sub[sub["model"] == m]
        if d.empty:
            ax.text(
                0.5,
                0.5,
                f"{m}\n(no data)",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=6,
            )
            ax.set_axis_off()
            continue
        folds = sorted(d["fold"].unique())
        data = [d.loc[d["fold"] == f, "residual"].to_numpy(dtype=float) for f in folds]
        ax.boxplot(data, showmeans=True)
        ax.set_xticks(np.arange(1, len(folds) + 1))
        ax.set_xticklabels([str(f) for f in folds], fontsize=4, rotation=45)
        ax.axhline(0.0, color="black", linewidth=0.45, linestyle="--")
        ax.set_title(m, fontsize=6)
        ax.tick_params(axis="y", labelsize=4)
        ax.grid(axis="y", alpha=0.25)

    for j in range(len(model_names), nrows * ncols):
        r, c = divmod(j, ncols)
        axes[r][c].axis("off")

    fig.suptitle(
        f"CV residuals by fold — {target} (all models; x = fold index)",
        fontsize=10,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
