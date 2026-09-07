"""
GPR native UQ: posterior std via sklearn's ``GaussianProcessRegressor.predict(
X, return_std=True)`` (spec.md §5.1). Not new math -- this reuses the pattern
already implemented and running in ``nolhc_ml/src/evaluate.py`` (the
``gpr_native`` block: median_std, mean_std, z_90pct * std as half-width), just
wired into the live trust score instead of sitting as a dormant offline artifact.

Covers 4 of 20 registered KPIs (WT_OB_NA_GB-Ross, WT_OB_LB, Uti_DAFM_D, Uti_DAFM_R).

T2.3 (26-27 Aug 2026, spec.md §6): real fit()/predict_with_uncertainty(), no
longer a stub. Reuses ``Z_90`` from evaluate.py directly (not a re-typed
approximation) and the exact gpr_rbf/gpr_matern kernel hyperparameters from
``candidate_models.CANDIDATE_MODELS`` -- the same architecture registry.json's
winner was chosen from. GPR is scale-sensitive (unlike RF/ExtraTrees), so
inputs are standardized internally, matching evaluate.py fitting on
``X_scaled`` rather than raw X.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.base import clone
from sklearn.preprocessing import StandardScaler

from .base import UncertaintyResult

_NOLHC_SRC = Path(__file__).resolve().parents[4] / "nolhc_ml" / "src"
if str(_NOLHC_SRC) not in sys.path:
    sys.path.insert(0, str(_NOLHC_SRC))

from candidate_models import CANDIDATE_MODELS  # noqa: E402
from evaluate import Z_90  # noqa: E402  -- exact constant, not a re-typed 1.645 approx


class GPRNative:
    """UQEstimator for GPR_RBF/GPR_Matern winners (spec.md §5.1 tier: GPR native)."""

    def __init__(self, kpi_slug: str, registered_as: str) -> None:
        if registered_as not in ("gpr_rbf", "gpr_matern"):
            raise KeyError(
                f"GPRNative only handles gpr_rbf/gpr_matern, got {registered_as!r} for {kpi_slug!r}"
            )
        self.kpi_slug = kpi_slug
        self.registered_as = registered_as
        self._fitted_model = None
        self._scaler: Optional[StandardScaler] = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "GPRNative":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D (n_samples, n_features), got shape {X.shape}")
        if len(X) != len(y):
            raise ValueError(f"X/y length mismatch: {len(X)} vs {len(y)}")
        if len(X) < 2:
            raise ValueError(f"need >=2 rows to fit, got {len(X)}")

        scaler = StandardScaler().fit(X)
        est = clone(CANDIDATE_MODELS[self.registered_as])
        est.fit(scaler.transform(X), y)

        self._scaler = scaler
        self._fitted_model = est
        return self

    def predict_with_uncertainty(self, X: np.ndarray) -> UncertaintyResult:
        if self._fitted_model is None or self._scaler is None:
            raise RuntimeError(f"GPRNative for {self.kpi_slug!r} not fitted -- call fit() first")
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D (n_samples, n_features), got shape {X.shape}")

        mean, std = self._fitted_model.predict(self._scaler.transform(X), return_std=True)
        half_width = Z_90 * std

        return UncertaintyResult(
            mean=mean,
            lower=mean - half_width,
            upper=mean + half_width,
            method="gpr_native",
        )
