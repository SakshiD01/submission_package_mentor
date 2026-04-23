"""
Step 3a: explicit per-target model ranking from CV (independent per target).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Sequence

import pandas as pd


def load_cv(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def top_k_models_by_cv_rmse(
    cv_results: Dict[str, Any],
    target: str,
    model_names: Sequence[str],
    k: int,
) -> List[str]:
    scored = [
        (m, float(cv_results[target][m]["mean_rmse"])) for m in model_names
    ]
    scored.sort(key=lambda x: x[1])
    return [m for m, _ in scored[: max(1, k)]]


def export_per_target_selection_table(
    cv_path: Path,
    model_names: Sequence[str],
    *,
    top_k: int = 3,
) -> pd.DataFrame:
    """
    One row per target: best CV-RMSE model, runners-up, and all mean RMSEs as context.
    Selection is **per target only** (no global winner).
    """
    cv = load_cv(cv_path)
    targets = sorted(cv.keys())
    rows = []
    for t in targets:
        order = top_k_models_by_cv_rmse(cv, t, model_names, len(model_names))
        best = order[0]
        second = order[1] if len(order) > 1 else ""
        third = order[2] if len(order) > 2 else ""
        rows.append(
            {
                "target": t,
                "best_cv_rmse_model": best,
                "mean_cv_rmse": cv[t][best]["mean_rmse"],
                "std_cv_rmse": cv[t][best]["std_rmse"],
                "rank2_model": second,
                "rank2_mean_cv_rmse": cv[t][second]["mean_rmse"] if second else "",
                "rank3_model": third,
                "rank3_mean_cv_rmse": cv[t][third]["mean_rmse"] if third else "",
                "n_models_compared": len(model_names),
            }
        )
    return pd.DataFrame(rows)
