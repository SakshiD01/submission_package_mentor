"""
Hold-out test evaluation: fixed nominal (e.g. 90%) symmetric conformal-style intervals
and residual diagnostics for reporting.

Uses test residuals only (same split as Step 7). Intervals are descriptive when
calibrated on the same hold-out used for scoring; see narrative caveats.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
from scipy import stats


def _safe_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", s)


def fixed_nominal_symmetric_intervals(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    nominal: float = 0.90,
) -> Dict[str, Any]:
    """
    Symmetric intervals: y_pred ± q, where q = nominal quantile of |y_true - y_pred|.

    Empirical coverage on the same points is reported; it need not equal ``nominal``
    for small n.
    """
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    residuals = y_true - y_pred
    scores = np.abs(residuals)
    q = float(np.quantile(scores, nominal))
    lower = y_pred - q
    upper = y_pred + q
    covered = (y_true >= lower) & (y_true <= upper)
    empirical = float(np.mean(covered))
    return {
        "nominal_coverage_requested": float(nominal),
        "quantile_abs_residual": q,
        "interval_half_width": q,
        "interval_width": 2.0 * q,
        "empirical_coverage": empirical,
        "n_points": len(y_true),
        "lower": lower,
        "upper": upper,
        "covered": covered,
        "residuals": residuals,
    }


def residual_diagnostic_flags(
    residuals: np.ndarray,
    y_true: np.ndarray,
    *,
    bias_sigma: float = 0.2,
    skew_tail: float = 1.0,
) -> Dict[str, Any]:
    """
    Heuristic flags for mentor review (not formal tests).

    bias_sigma: flag if |mean(residual)| > bias_sigma * std(y_true) (scale-aware).
    skew_tail: flag if |skew(residuals)| > skew_tail.
    """
    r = np.asarray(residuals, dtype=float).ravel()
    y = np.asarray(y_true, dtype=float).ravel()
    std_y = float(np.std(y, ddof=1)) if len(y) > 1 else 1.0
    mean_r = float(np.mean(r))
    std_r = float(np.std(r, ddof=1)) if len(r) > 1 else 0.0
    sk = float(stats.skew(r, bias=False)) if len(r) > 2 else 0.0
    kt = float(stats.kurtosis(r, bias=False)) if len(r) > 3 else 0.0

    bias_thresh = bias_sigma * max(std_y, 1e-12)
    flag_bias = abs(mean_r) > bias_thresh
    flag_heavy_tail = abs(sk) > skew_tail or kt > 3.0

    return {
        "mean_residual": mean_r,
        "std_residual": std_r,
        "skew_residual": sk,
        "excess_kurtosis_residual": kt,
        "bias_threshold_used": bias_thresh,
        "flag_systematic_bias": flag_bias,
        "flag_heavy_or_skewed_tails": flag_heavy_tail,
    }


def plot_holdout_residual_panel(
    target: str,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    out_path: Path,
    *,
    nominal: float = 0.90,
) -> None:
    """One figure: residual vs fitted, histogram, QQ (normal)."""
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    residuals = y_true - y_pred

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    fig.suptitle(
        f"{target} — hold-out residuals (n={len(y_true)}), nominal {nominal:.0%} intervals in tables",
        fontsize=11,
    )

    ax = axes[0]
    ax.scatter(y_pred, residuals, alpha=0.75, s=28, edgecolors="k", linewidths=0.3)
    ax.axhline(0.0, color="gray", linestyle="--", linewidth=1)
    ax.set_xlabel("Fitted (ŷ) on hold-out")
    ax.set_ylabel("Residual (y − ŷ)")
    ax.set_title("Residual vs fitted")

    ax = axes[1]
    ax.hist(residuals, bins=min(12, max(5, len(residuals) // 3)), color="steelblue", edgecolor="white")
    ax.axvline(0.0, color="gray", linestyle="--", linewidth=1)
    ax.set_xlabel("Residual")
    ax.set_title("Residual histogram")

    ax = axes[2]
    stats.probplot(residuals, dist="norm", plot=ax)
    ax.set_title("Normal Q-Q (residuals)")

    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close()


def build_narrative_markdown(
    *,
    out_rel: str,
    figures: List[str],
    summary_rows: List[Dict[str, Any]],
    n_holdout: int,
    nominal: float,
) -> str:
    lines = [
        "# Test set evaluation — hold-out (finalization step 2)",
        "",
        "## Scope",
        f"- **Hold-out fraction:** 20% of design rows (see `trained_models/split_meta.json`); **not** used in CV or training.",
        f"- **Nominal coverage for intervals:** **{nominal:.0%}** (fixed symmetric intervals in summary tables below).",
        "- **Caveat:** Intervals use the absolute residual quantile on the **same** hold-out points used for RMSE; interpret as **descriptive** marginal coverage, not full split-conformal guarantees.",
        "",
        "## Point predictions + intervals",
        f"- Long table: `{out_rel}/selected_holdout_predictions_long.csv` — one row per hold-out point and selected model per target (y, ŷ, residual, **{nominal:.0%}** lower/upper).",
        f"- Per-target summary: `{out_rel}/selected_holdout_summary.csv` — RMSE/MAE/R², **{nominal:.0%}** quantile half-width, empirical coverage, diagnostic flags.",
        "",
        "## Single narrative: point error + interval width + residual behaviour",
    ]
    for row in summary_rows:
        t = row["target"]
        lines.append(
            f"- **{t}** ({row['selected_model']}): test RMSE={row['test_rmse']:.6g}, "
            f"{nominal:.0%} interval half-width q=|r| quantile={row['quantile_abs_residual']:.6g}, "
            f"empirical coverage={row['empirical_coverage_90']:.3f}, "
            f"bias_flag={row['flag_systematic_bias']}, tail_flag={row['flag_heavy_or_skewed_tails']}."
        )
    lines.extend(
        [
            "",
            "## Figures (residual diagnostics)",
            f"- Hold-out size **n = {n_holdout}** per target.",
        ]
    )
    for fig in figures:
        lines.append(f"- `{fig}`")
    lines.extend(["", "## Tabular summary (copy into final report)", ""])
    hdr = "| target | model | RMSE | MAE | R² | q(|r|) at nominal | empirical cov. | width 2q | bias? | tails? |"
    sep = "|---|---|--:|--:|--:|--:|--:|--:|:--:|:--:|"
    lines.append(hdr)
    lines.append(sep)
    for row in summary_rows:
        lines.append(
            f"| {row['target']} | {row['selected_model']} | {row['test_rmse']:.6g} | {row['test_mae']:.6g} | "
            f"{row['test_r2']:.4f} | {row['quantile_abs_residual']:.6g} | {row['empirical_coverage_90']:.3f} | "
            f"{row['interval_width_90']:.6g} | {row['flag_systematic_bias']} | {row['flag_heavy_or_skewed_tails']} |"
        )
    lines.append("")
    return "\n".join(lines)
