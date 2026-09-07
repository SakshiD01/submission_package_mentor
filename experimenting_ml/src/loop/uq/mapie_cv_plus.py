"""
MapieCVPlus: wraps mapie's CV+ (jackknife+/CV+ family, method="plus") behind
the UQEstimator interface -- spec.md's PROVEN_6 benchmark (29-Aug,
UQ_Method_Benchmark.xlsx) found this beats plain split-conformal for
ElasticNet and GradientBoosting specifically: closer to the 90% nominal
coverage target at comparable or better interval width, on real held-out
data.

Not part of the generic, registry-driven dispatch (dispatch.py's
bagged_tree_native/gpr_native/conformal_fallback) -- deliberately kept
separate. The winning method in PROVEN_6 differs per KPI/family in a way
that isn't a clean "if registered_as in X" rule the way the 3 main paths
are (e.g. GPR-Matern's winner was the CONFORMAL path, not its own native
path) -- see proven6.py for the explicit, hand-curated table this backs.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.base import clone
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .base import UncertaintyResult

_NOLHC_SRC = Path(__file__).resolve().parents[4] / "nolhc_ml" / "src"
if str(_NOLHC_SRC) not in sys.path:
    sys.path.insert(0, str(_NOLHC_SRC))

from candidate_models import CANDIDATE_MODELS  # noqa: E402


class MapieCVPlus:
    """UQEstimator wrapping mapie.regression.MapieRegressor(method="plus")."""

    def __init__(
        self,
        kpi_slug: str,
        registered_as: str,
        alpha: float = 0.10,
        cv: int = 5,
        needs_scaling: bool = True,
    ) -> None:
        if registered_as not in CANDIDATE_MODELS:
            raise KeyError(
                f"{registered_as!r} not a known candidate model for {kpi_slug!r}: "
                f"{sorted(CANDIDATE_MODELS)}"
            )
        self.kpi_slug = kpi_slug
        self.registered_as = registered_as
        self.alpha = alpha  # 0.10 -> 90% interval, matching every other dispatch path's default
        self.cv = cv
        self.needs_scaling = needs_scaling
        self._mapie = None

    def _build_estimator(self):
        base = clone(CANDIDATE_MODELS[self.registered_as])
        if self.needs_scaling:
            return Pipeline([("scale", StandardScaler()), ("est", base)])
        return base

    def fit(self, X: np.ndarray, y: np.ndarray) -> "MapieCVPlus":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D (n_samples, n_features), got shape {X.shape}")
        if len(X) != len(y):
            raise ValueError(f"X/y length mismatch: {len(X)} vs {len(y)}")
        if len(X) < self.cv:
            raise ValueError(f"need >={self.cv} rows for {self.cv}-fold CV+, got {len(X)}")

        from mapie.regression import MapieRegressor

        mapie_reg = MapieRegressor(
            estimator=self._build_estimator(), method="plus", cv=self.cv, random_state=42
        )
        mapie_reg.fit(X, y)
        self._mapie = mapie_reg
        return self

    def predict_with_uncertainty(self, X: np.ndarray) -> UncertaintyResult:
        if self._mapie is None:
            raise RuntimeError(f"MapieCVPlus for {self.kpi_slug!r} not fitted -- call fit() first")
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D (n_samples, n_features), got shape {X.shape}")

        y_pred, y_pis = self._mapie.predict(X, alpha=self.alpha)
        lower = y_pis[:, 0, 0]
        upper = y_pis[:, 1, 0]

        return UncertaintyResult(mean=y_pred, lower=lower, upper=upper, method="mapie_cv_plus")
