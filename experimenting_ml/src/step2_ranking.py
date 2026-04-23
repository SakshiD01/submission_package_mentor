"""
Mentor Step 2a: Friedman test + Nemenyi post-hoc on aligned CV validation RMSEs.

Uses the per-model ``fold_rmses`` vectors from ``cv_results.json``. Those scores are
out-of-fold errors on the *training pool* (103 rows), with identical split order for
every model — suitable for Friedman / Nemenyi as repeated-measures across folds.

Note: The held-out 26-row test set yields **one** RMSE per model per target, so it
cannot feed Friedman (needs multiple related blocks). Holdout metrics stay in
``test_results`` for final reporting.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, rankdata

try:
    import scikit_posthocs as sp
except ImportError as e:
    sp = None  # type: ignore
    _SP_ERR = e
else:
    _SP_ERR = None


def load_cv_results(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_fold_rmse_matrix(
    cv_results: Dict[str, Any],
    target: str,
    model_names: List[str],
) -> pd.DataFrame:
    """
    Rows = fold index (1..N), columns = model names, values = RMSE on that fold.
    """
    cols = {}
    n_list = []
    for m in model_names:
        fr = cv_results[target][m]["fold_rmses"]
        arr = np.asarray(fr, dtype=float).ravel()
        cols[m] = arr
        n_list.append(len(arr))
    if len(set(n_list)) != 1:
        raise ValueError(
            f"{target}: models have different fold_rmses lengths {set(n_list)} — "
            "rerun CV with the same scheme for all models (e.g. repeated 10-fold)."
        )
    n = n_list[0]
    if n < 3:
        raise ValueError(f"{target}: need at least 3 CV scores per model, got {n}")
    idx = pd.RangeIndex(start=1, stop=n + 1, name="fold")
    return pd.DataFrame(cols, index=idx)


def average_ranks_low_better(matrix: pd.DataFrame) -> pd.Series:
    """Per fold, rank models by RMSE (1 = best); return mean rank per model."""
    r = np.zeros(matrix.shape)
    for i in range(len(matrix)):
        r[i, :] = rankdata(matrix.iloc[i].values, method="average")
    return pd.Series(r.mean(axis=0), index=matrix.columns, name="mean_rank")


def friedman_test(matrix: pd.DataFrame) -> Tuple[float, float]:
    """scipy Friedman: one sample per treatment, each of length n_blocks."""
    samples = [matrix[c].values for c in matrix.columns]
    stat, p = friedmanchisquare(*samples)
    return float(stat), float(p)


def nemenyi_posthoc(matrix: pd.DataFrame) -> pd.DataFrame:
    if sp is None:
        raise ImportError(
            "scikit-posthocs is required for Nemenyi. pip install scikit-posthocs"
        ) from _SP_ERR
    # Rows = blocks (folds), columns = groups (models)
    x = matrix.values
    return sp.posthoc_nemenyi_friedman(x)


def summarize_tiers(
    avg_rank: pd.Series,
    nemenyi_p: pd.DataFrame,
    alpha: float = 0.05,
) -> List[str]:
    """
    Rough tier labels: models not significantly different (p >= alpha) to the
    best-ranked model form tier 1; extend greedily.
    """
    order = avg_rank.sort_values().index.tolist()
    best = order[0]
    tier1 = {best}
    for m in order[1:]:
        a, b = (best, m) if best < m else (m, best)
        if a not in nemenyi_p.index or b not in nemenyi_p.columns:
            continue
        p = float(nemenyi_p.loc[a, b])
        if p >= alpha:
            tier1.add(m)
    return sorted(tier1, key=lambda x: avg_rank[x])


def run_ranking_for_all_targets(
    cv_path: Path,
    model_names: List[str],
    targets: List[str],
    *,
    alpha: float = 0.05,
) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame], Dict[str, Any]]:
    cv = load_cv_results(cv_path)
    summary_rows = []
    nemenyi_by_target: Dict[str, pd.DataFrame] = {}
    meta: Dict[str, Any] = {"alpha": alpha, "method": "Friedman + Nemenyi (CV fold RMSEs)"}

    for target in targets:
        mat = build_fold_rmse_matrix(cv, target, model_names)
        stat, p = friedman_test(mat)
        avg_r = average_ranks_low_better(mat)
        nemenyi = nemenyi_posthoc(mat)
        nemenyi_by_target[target] = nemenyi
        tier1 = summarize_tiers(avg_r, nemenyi, alpha=alpha)
        summary_rows.append(
            {
                "target": target,
                "n_blocks": len(mat),
                "n_models": len(model_names),
                "friedman_statistic": stat,
                "friedman_p_value": p,
                "best_mean_rank_model": avg_r.idxmin(),
                "best_mean_rank": float(avg_r.min()),
                "tier1_not_sig_vs_best": ";".join(tier1),
            }
        )
        meta[target] = {"mean_ranks": avg_r.to_dict()}

    return pd.DataFrame(summary_rows), nemenyi_by_target, meta


def critical_difference(
    n_models: int,
    n_blocks: int,
    *,
    alpha: float = 0.05,
) -> float:
    """
    Nemenyi critical difference for average ranks (Demšar 2006).
    CD = q_alpha * sqrt(k*(k+1)/(6*N)) with k models, N blocks.
    q_alpha uses studentized range approximation (infinite df).
    """
    from scipy.stats import studentized_range

    k = n_models
    n = n_blocks
    q = float(studentized_range.ppf(1.0 - alpha, k, np.inf))
    return q * np.sqrt(k * (k + 1) / (6.0 * n))


def shortlist_by_median_mean_rank(
    cv_path: Path,
    model_names: List[str],
    targets: List[str],
    *,
    k: int = 5,
) -> List[str]:
    """
    Pick ``k`` models with the lowest median average-rank (across targets).
    """
    cv = load_cv_results(cv_path)
    ranks: Dict[str, List[float]] = {m: [] for m in model_names}
    for t in targets:
        mat = build_fold_rmse_matrix(cv, t, model_names)
        ar = average_ranks_low_better(mat)
        for m in model_names:
            ranks[m].append(float(ar[m]))
    med = {m: float(np.median(v)) for m, v in ranks.items()}
    ordered = sorted(med.keys(), key=lambda x: med[x])
    return ordered[: max(1, int(k))]
