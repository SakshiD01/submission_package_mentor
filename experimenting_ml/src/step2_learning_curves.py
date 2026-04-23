"""
Mentor Step 2c: Learning curves (train vs CV validation RMSE vs training-set size).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import matplotlib.pyplot as plt
import numpy as np
from sklearn.base import clone
from sklearn.metrics import make_scorer, mean_squared_error
from sklearn.model_selection import KFold, learning_curve
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from models import NEEDS_SCALING, get_models


def _rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


_RMSE_SCORER = make_scorer(_rmse, greater_is_better=False)


def _estimator_for_model(model_name: str, best_params: dict):
    """
    Match Step 1 CV: StandardScaler before the base estimator when NEEDS_SCALING
    (including Pipeline models like PolynomialReg).
    """
    cfg = get_models()[model_name]
    inner = clone(cfg["model"])
    inner.set_params(**best_params)
    if model_name in NEEDS_SCALING:
        return Pipeline([("scaler", StandardScaler()), ("est", inner)])
    return inner


def _train_sizes(n_samples: int, cv_splits: int, n_points: int = 6) -> np.ndarray:
    # learning_curve caps at largest training chunk usable under KFold(cv_splits)
    n_max = int(n_samples * (cv_splits - 1) / cv_splits)
    n_max = max(n_max, cv_splits)
    lo = max(cv_splits, int(0.12 * n_max))
    hi = n_max
    if lo >= hi:
        return np.array([hi], dtype=int)
    sizes = np.unique(
        np.linspace(lo, hi, num=min(n_points, max(2, hi - lo + 1))).astype(int)
    )
    return np.clip(sizes, 1, n_max)


def learning_curve_statistics(
    X: np.ndarray,
    y: np.ndarray,
    model_name: str,
    best_params: dict,
    *,
    cv_splits: int = 5,
    random_state: int = 42,
    n_train_sizes: int = 6,
    n_jobs: int = -1,
):
    """Returns sizes, train_mean, train_std, val_mean, val_std."""
    est = _estimator_for_model(model_name, best_params)
    cv = KFold(n_splits=cv_splits, shuffle=True, random_state=random_state)
    requested_sizes = _train_sizes(len(X), cv_splits, n_points=n_train_sizes)
    sizes, train_scores, val_scores = learning_curve(
        est,
        X,
        y,
        train_sizes=requested_sizes,
        cv=cv,
        scoring=_RMSE_SCORER,
        n_jobs=n_jobs,
        random_state=random_state,
    )
    train_mean = np.mean(train_scores, axis=1)
    train_std = np.std(train_scores, axis=1)
    val_mean = np.mean(val_scores, axis=1)
    val_std = np.std(val_scores, axis=1)
    return sizes, train_mean, train_std, val_mean, val_std


def plot_learning_curve_one(
    X: np.ndarray,
    y: np.ndarray,
    model_name: str,
    best_params: dict,
    out_path: Path,
    *,
    cv_splits: int = 5,
    random_state: int = 42,
    n_train_sizes: int = 6,
    title_suffix: str = "",
) -> None:
    sizes, train_mean, train_std, val_mean, val_std = learning_curve_statistics(
        X,
        y,
        model_name,
        best_params,
        cv_splits=cv_splits,
        random_state=random_state,
        n_train_sizes=n_train_sizes,
        n_jobs=-1,
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(sizes, train_mean, "o-", label="Train RMSE (CV)", color="tab:blue")
    ax.fill_between(
        sizes,
        train_mean - train_std,
        train_mean + train_std,
        alpha=0.2,
        color="tab:blue",
    )
    ax.plot(
        sizes,
        val_mean,
        "o-",
        label="Validation RMSE (CV)",
        color="tab:orange",
    )
    ax.fill_between(
        sizes,
        val_mean - val_std,
        val_mean + val_std,
        alpha=0.2,
        color="tab:orange",
    )
    ax.set_xlabel("Training set size")
    ax.set_ylabel("RMSE")
    ax.set_title(f"Learning curve — {model_name}{title_suffix}")
    ax.legend(loc="best")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_learning_curves_shortlist(
    X_train: np.ndarray,
    y_train: np.ndarray,
    cv_results: Dict[str, Any],
    target: str,
    shortlist: Sequence[str],
    out_dir: Path,
    *,
    cv_splits: int = 5,
    random_state: int = 42,
) -> List[Path]:
    paths = []
    for m in shortlist:
        bp = cv_results[target][m]["best_params"]
        outp = out_dir / f"learning_curve__{target}__{m}.png"
        plot_learning_curve_one(
            X_train,
            y_train,
            m,
            bp,
            outp,
            cv_splits=cv_splits,
            random_state=random_state,
            title_suffix=f" | {target}",
        )
        paths.append(outp)
    return paths


def plot_learning_curves_grid_all_models(
    X_train: np.ndarray,
    y_train: np.ndarray,
    cv_results: Dict[str, Any],
    target: str,
    model_names: Sequence[str],
    out_path: Path,
    *,
    cv_splits: int = 5,
    random_state: int = 42,
    n_train_sizes: int = 5,
    dpi: int = 110,
) -> Path:
    """
    One figure per target: all models in a subplot grid (train=blue, val=orange).
    Uses n_jobs=1 inside each call to avoid oversubscription when many models run in serial.
    """
    n = len(model_names)
    ncols = 4
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(3.0 * ncols, 2.4 * nrows), squeeze=False
    )
    last_idx = -1
    for idx, m in enumerate(model_names):
        last_idx = idx
        r, c = divmod(idx, ncols)
        ax = axes[r][c]
        bp = cv_results[target][m]["best_params"]
        try:
            sizes, tm, _ts, vm, _vs = learning_curve_statistics(
                X_train,
                y_train,
                m,
                bp,
                cv_splits=cv_splits,
                random_state=random_state,
                n_train_sizes=n_train_sizes,
                n_jobs=1,
            )
            ax.plot(sizes, tm, "-", color="tab:blue", linewidth=0.9, label="tr")
            ax.plot(sizes, vm, "-", color="tab:orange", linewidth=0.9, label="val")
        except Exception:
            ax.text(
                0.5,
                0.5,
                f"{m}\n(error)",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=6,
            )
        ax.set_title(m, fontsize=7)
        ax.tick_params(axis="both", labelsize=5)
        ax.grid(alpha=0.25)

    for j in range(last_idx + 1, nrows * ncols):
        r, c = divmod(j, ncols)
        axes[r][c].axis("off")

    fig.suptitle(
        f"Learning curves — {target}\n(blue=train RMSE, orange=val RMSE; 5-fold CV)",
        fontsize=10,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    return out_path
