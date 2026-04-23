"""
Step 3c: OOF calibration diagnostics on CV folds (before conformal on test).

Uses pooled out-of-fold y vs ŷ to report bias, correlation, regression slope of y on ŷ,
and a binned calibration plot (mean actual vs mean predicted by quantile bin).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from step3_selection import top_k_models_by_cv_rmse


def _metrics(y: np.ndarray, yhat: np.ndarray) -> Dict[str, float]:
    y = np.asarray(y, dtype=float).ravel()
    yhat = np.asarray(yhat, dtype=float).ravel()
    res = y - yhat
    if len(y) < 3:
        return {
            "n_oof": float(len(y)),
            "mean_residual": float(np.nan),
            "std_residual": float(np.nan),
            "corr_y_yhat": float(np.nan),
            "slope_y_on_yhat": float(np.nan),
        }
    slope, intercept = np.polyfit(yhat, y, 1)
    corr = float(np.corrcoef(y, yhat)[0, 1]) if np.std(yhat) > 0 and np.std(y) > 0 else float("nan")
    return {
        "n_oof": float(len(y)),
        "mean_residual": float(np.mean(res)),
        "std_residual": float(np.std(res, ddof=1)),
        "corr_y_yhat": corr,
        "slope_y_on_yhat": float(slope),
        "intercept_y_on_yhat": float(intercept),
    }


def _binned_means(
    y: np.ndarray, yhat: np.ndarray, n_bins: int = 8
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    y = np.asarray(y, dtype=float).ravel()
    yhat = np.asarray(yhat, dtype=float).ravel()
    order = np.argsort(yhat)
    y, yhat = y[order], yhat[order]
    edges = np.quantile(yhat, np.linspace(0, 1, n_bins + 1))
    edges[0] = yhat.min() - 1e-12
    edges[-1] = yhat.max() + 1e-12
    xb, yb, se = [], [], []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (yhat >= lo) & (yhat <= hi) if i == n_bins - 1 else (yhat >= lo) & (yhat < hi)
        if not np.any(mask):
            continue
        yb.append(float(np.mean(y[mask])))
        xb.append(float(np.mean(yhat[mask])))
        se.append(float(np.std(y[mask], ddof=1) / np.sqrt(np.sum(mask))))
    return np.array(xb), np.array(yb), np.array(se)


def plot_calibration_figure(
    y: np.ndarray,
    yhat: np.ndarray,
    out_path: Path,
    *,
    title: str,
    n_bins: int = 8,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    ax = axes[0]
    ax.scatter(yhat, y, alpha=0.35, s=12, edgecolors="none")
    lims = [
        min(y.min(), yhat.min()),
        max(y.max(), yhat.max()),
    ]
    ax.plot(lims, lims, "k--", lw=1, label="y = ŷ")
    ax.set_xlabel("Predicted (OOF)")
    ax.set_ylabel("Actual (OOF)")
    ax.set_title("OOF scatter")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)

    ax2 = axes[1]
    xb, yb, _ = _binned_means(y, yhat, n_bins=n_bins)
    ax2.errorbar(xb, yb, fmt="o-", capsize=3, markersize=5)
    lim2 = [min(xb.min(), yb.min()), max(xb.max(), yb.max())]
    ax2.plot(lim2, lim2, "k--", lw=1, label="perfect calibration")
    ax2.set_xlabel("Mean predicted (bin)")
    ax2.set_ylabel("Mean actual (bin)")
    ax2.set_title("Binned calibration (quantile bins on ŷ)")
    ax2.legend(loc="upper left")
    ax2.grid(alpha=0.3)

    fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=130)
    plt.close(fig)


def calibration_for_top_models(
    df: pd.DataFrame,
    cv_results: Dict[str, Any],
    *,
    targets: Sequence[str],
    model_names: Sequence[str],
    out_dir: Path,
    top_k: int = 3,
) -> pd.DataFrame:
    """
    ``df`` must have columns target, model, y_true, y_pred (OOF pooled over folds).
    Only the top ``top_k`` models by CV mean RMSE per target are evaluated.
    """
    rows: List[Dict[str, Any]] = []
    for t in targets:
        tops = top_k_models_by_cv_rmse(cv_results, t, model_names, top_k)
        for m in tops:
            sub = df[(df["target"] == t) & (df["model"] == m)]
            if len(sub) < 3:
                continue
            y = sub["y_true"].to_numpy(dtype=float)
            yhat = sub["y_pred"].to_numpy(dtype=float)
            met = _metrics(y, yhat)
            slope = met["slope_y_on_yhat"]
            sy = float(np.std(y))
            bias_ok = abs(met["mean_residual"]) <= max(1e-9, 0.05 * max(sy, 1e-9))
            slope_ok = not np.isnan(slope) and 0.75 <= slope <= 1.25
            met_row = {
                "target": t,
                "model": m,
                **met,
                "heuristic_ok_bias": bias_ok,
                "heuristic_ok_slope": slope_ok,
            }
            rows.append(met_row)
            plot_calibration_figure(
                y,
                yhat,
                out_dir / f"calibration__{t}__{m}.png",
                title=f"OOF calibration — {t} / {m}",
            )
    return pd.DataFrame(rows)
