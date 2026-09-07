"""UQ estimators: one uniform interface, three dispatch paths (spec.md §5.1)."""

from __future__ import annotations

from .base import UncertaintyResult, UQEstimator
from .dispatch import DispatchPath, classify_kpi, get_uq_estimator, kpis_by_path, load_registry

__all__ = [
    "UncertaintyResult",
    "UQEstimator",
    "DispatchPath",
    "classify_kpi",
    "get_uq_estimator",
    "kpis_by_path",
    "load_registry",
]
