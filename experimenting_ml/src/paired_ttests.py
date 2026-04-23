"""
Round-robin paired t-tests on CV fold RMSEs (ML_Pipeline_Specification.md §8).
"""

from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, List, Optional

import numpy as np
from scipy.stats import ttest_rel


def run_paired_ttests(
    cv_results: Dict[str, Dict[str, Any]],
    *,
    model_names: Optional[List[str]] = None,
    alpha: float = 0.05,
) -> List[dict]:
    """
    For each target, compare every pair of models with scipy.stats.ttest_rel
    on the stored CV validation RMSEs (one per split; e.g. 5 for KFold or 30 for 10×3 repeated).

    Returns one row per (target, model_i, model_j) with i < j in model_names order.
    """
    if model_names is None:
        first = next(iter(cv_results))
        mnames = sorted(cv_results[first].keys())
    else:
        mnames = list(model_names)
    rows: List[dict] = []

    for target, per_model in cv_results.items():
        for model_i, model_j in combinations(mnames, 2):
            ri = np.asarray(per_model[model_i]["fold_rmses"], dtype=float)
            rj = np.asarray(per_model[model_j]["fold_rmses"], dtype=float)
            if ri.shape != rj.shape or ri.ndim != 1 or ri.size < 2:
                raise ValueError(
                    f"{target}: paired fold_rmses must match and have length ≥ 2 for "
                    f"{model_i}/{model_j}, got {ri.shape}/{rj.shape}"
                )

            t_stat, p_value = ttest_rel(ri, rj)
            p_value = float(p_value)
            t_stat = float(t_stat)
            mean_i, mean_j = float(np.mean(ri)), float(np.mean(rj))
            significant = p_value < alpha
            if mean_i < mean_j:
                better = model_i
            elif mean_j < mean_i:
                better = model_j
            else:
                better = ""

            rows.append(
                {
                    "target": target,
                    "Model_A": model_i,
                    "Model_B": model_j,
                    "Mean_RMSE_A": mean_i,
                    "Mean_RMSE_B": mean_j,
                    "t_stat": t_stat,
                    "p_value": p_value,
                    "Significant": significant,
                    "Better_Model": better,
                }
            )

    return rows
