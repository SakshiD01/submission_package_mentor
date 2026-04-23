"""
Step 9: adaptive split conformal intervals from test residuals (spec §9).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from models import get_models


def _coverage_for_relative_error(relative_error: float) -> float:
    if relative_error <= 1.05:
        return 0.90
    if relative_error <= 1.20:
        return 0.95
    return 0.99


def compute_conformal_results(
    test_results: Dict[str, Dict[str, Dict[str, Any]]],
    y_test_by_target: Dict[str, np.ndarray],
    *,
    model_names: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    For each target and model: pick adaptive coverage from test RMSE vs best RMSE,
    then quantile of |residuals| on test points; report empirical coverage and width.
    """
    mnames = model_names or list(get_models().keys())
    out: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for target, per_m in test_results.items():
        y_true = np.asarray(y_test_by_target[target], dtype=float)
        best_rmse = min(per_m[m]["rmse"] for m in mnames)
        out[target] = {}

        for mname in mnames:
            r = per_m[mname]
            rel = r["rmse"] / best_rmse if best_rmse > 0 else float("inf")
            coverage = _coverage_for_relative_error(rel)

            y_pred = np.asarray(r["y_pred"], dtype=float)
            residuals = np.asarray(r["residuals"], dtype=float)
            scores = np.abs(residuals)
            q = float(np.quantile(scores, coverage))

            lower = y_pred - q
            upper = y_pred + q
            empirical = float(
                np.mean((y_true >= lower) & (y_true <= upper))
            )

            out[target][mname] = {
                "coverage_level": coverage,
                "relative_rmse_to_best": float(rel),
                "quantile": q,
                "empirical_coverage": empirical,
                "interval_width": 2.0 * q,
            }

    return out
