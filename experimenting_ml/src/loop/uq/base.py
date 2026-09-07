"""
UQEstimator interface -- the uniform contract every dispatch path implements
(spec.md §5.1): "Both paths emit the same normalized interval/score shape so
the loop's threshold logic doesn't care which family produced it."

loop.py and trust.py talk to this interface only. They never branch on model
family -- that branching happens once, in dispatch.py, at KPI-selection time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np


@dataclass(frozen=True)
class UncertaintyResult:
    """Same shape regardless of which of the three dispatch paths produced it."""

    mean: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    method: str  # "bagged_tree_jackknife" | "gpr_native" | "conformal_fallback"

    def __post_init__(self) -> None:
        if not (self.mean.shape == self.lower.shape == self.upper.shape):
            raise ValueError(
                f"mean/lower/upper shape mismatch: {self.mean.shape}, "
                f"{self.lower.shape}, {self.upper.shape}"
            )

    @property
    def width(self) -> np.ndarray:
        return self.upper - self.lower

    def normalized_width(self, scale: float) -> np.ndarray:
        """Width divided by a KPI-specific scale (e.g. training std or IQR) so
        widths are comparable across KPIs with very different units and ranges
        (hours vs. fractions) -- required before combining into trust_score()
        (spec.md §5.1, T2.6)."""
        if scale <= 0:
            raise ValueError(f"scale must be positive, got {scale}")
        return self.width / scale


@runtime_checkable
class UQEstimator(Protocol):
    """Implemented by BaggedTreeJackknife, GPRNative, and ConformalFallback (T2.3)."""

    def fit(self, X: np.ndarray, y: np.ndarray) -> "UQEstimator":
        """Fit on the KPI's training rows. Returns self."""
        ...

    def predict_with_uncertainty(self, X: np.ndarray) -> UncertaintyResult:
        """Point prediction + interval for each row of X, same shape from every path."""
        ...
