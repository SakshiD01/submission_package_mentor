"""
Infer RepeatedKFold / KFold settings from cv_results.json for Step 2 diagnostics.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple


def infer_cv_config(cv_results: Dict[str, Any]) -> Tuple[int, int, int]:
    """
    Returns (n_splits, n_repeats, n_scores) consistent with stored fold_rmses.
    """
    first_target = next(iter(cv_results))
    first_model = next(iter(cv_results[first_target]))
    r0 = cv_results[first_target][first_model]
    fold_rmses = r0.get("fold_rmses") or []
    L = len(fold_rmses)
    if L < 1:
        raise ValueError("cv_results: missing fold_rmses")

    ns = r0.get("cv_n_splits")
    nr = r0.get("cv_n_repeats")
    if ns is not None and nr is not None:
        if int(ns) * int(nr) != L:
            raise ValueError(
                f"cv_n_splits×cv_n_repeats ({ns}×{nr}) != len(fold_rmses) ({L})"
            )
        return int(ns), int(nr), L

    if L == 5:
        return 5, 1, L
    if L == 10:
        return 10, 1, L
    if L % 10 == 0:
        return 10, L // 10, L
    raise ValueError(
        f"Cannot infer CV scheme from len(fold_rmses)={L}; rerun CV or pass "
        "--n-splits / --n-repeats explicitly."
    )
