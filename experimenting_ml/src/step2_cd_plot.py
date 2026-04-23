"""
Mentor Step 2b: Critical Difference (CD) diagram from average ranks (Nemenyi-style).
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from step2_ranking import average_ranks_low_better, critical_difference


def plot_cd_diagram(
    matrix: pd.DataFrame,
    out_path: Path,
    *,
    title: str,
    alpha: float = 0.05,
    figsize: tuple = (10, 5),
) -> None:
    """
    Horizontal axis = average rank (lower is better). Models within CD of each other
    are connected by a thick bar (approximate visual).
    """
    avg_rank = average_ranks_low_better(matrix)
    k = len(avg_rank)
    n_blocks = len(matrix)
    cd = critical_difference(k, n_blocks, alpha=alpha)

    order = avg_rank.sort_values().index.tolist()
    ranks = avg_rank.loc[order].values

    fig, ax = plt.subplots(figsize=figsize)
    y_pos = np.arange(len(order))

    ax.scatter(ranks, y_pos, s=80, zorder=3, color="tab:blue")
    for i, (name, r) in enumerate(zip(order, ranks)):
        ax.text(r + 0.08, i, name, va="center", fontsize=9)

    # Link consecutive models (in rank order) when |Δrank| < CD (Nemenyi-style)
    for i in range(len(order) - 1):
        a, b = order[i], order[i + 1]
        ra, rb = avg_rank[a], avg_rank[b]
        if abs(rb - ra) <= cd:
            ax.plot(
                [ra, rb],
                [i, i + 1],
                color="gray",
                linewidth=4,
                alpha=0.45,
                zorder=1,
            )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(order)
    ax.set_xlabel("Average rank (lower is better)")
    ax.set_title(f"{title}\nCD (α={alpha}) ≈ {cd:.3f}")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_cd_cross_target_mean_rank(
    matrices_by_target: dict,
    model_names: Sequence[str],
    out_path: Path,
    *,
    alpha: float = 0.05,
) -> None:
    """
    Average the *mean rank* of each model across targets, then one CD diagram.
    Uses mean block count across targets for CD (approximate visual).
    """
    acc = {m: [] for m in model_names}
    n_blocks_list = []
    for target, mat in matrices_by_target.items():
        ar = average_ranks_low_better(mat)
        n_blocks_list.append(len(mat))
        for m in model_names:
            acc[m].append(ar[m])
    mean_r = pd.Series({m: float(np.mean(v)) for m, v in acc.items()})
    # Synthetic "matrix" for plotting: repeat mean rank as constant rows (degenerate);
    # instead draw manually with CD based on average n_blocks
    n_blocks = int(round(np.mean(n_blocks_list)))
    k = len(model_names)
    cd = critical_difference(k, n_blocks, alpha=alpha)

    order = mean_r.sort_values().index.tolist()
    ranks = mean_r.loc[order].values

    fig, ax = plt.subplots(figsize=(10, 5))
    y_pos = np.arange(len(order))
    ax.scatter(ranks, y_pos, s=80, zorder=3, color="tab:green")
    for i, (name, r) in enumerate(zip(order, ranks)):
        ax.text(r + 0.05, i, name, va="center", fontsize=9)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(order)
    ax.set_xlabel("Mean of per-target average ranks (lower is better)")
    ax.set_title(
        f"Cross-target mean rank summary (approx. CD, N≈{n_blocks} folds)\nCD (α={alpha}) ≈ {cd:.3f}"
    )
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
