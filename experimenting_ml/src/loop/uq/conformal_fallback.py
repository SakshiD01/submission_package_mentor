"""
Conformal fallback UQ: split-conformal intervals behind the uniform
UQEstimator interface (spec.md §5.1) -- the safe default for the 13 of 20
KPIs whose registered winner is boosting, SVR, linear, polynomial, KNN, MLP,
AdaBoost, or a stacking ensemble of these.

T2.3 (26-27 Aug 2026, spec.md §6): real fit()/predict_with_uncertainty(), no
longer a stub. Reuses two pieces of already-built logic rather than
reinventing them:

  - ``nolhc_ml/src/evaluate.py``'s ``_rebuild_estimator()`` to reconstruct the
    exact un-fit architecture registry.json's winner was chosen from
    (including StackingRegressor for the "stacking" winners), so this class
    covers all 13 conformal-fallback KPIs generically, not just simple models.
  - ``conformal_predict.py``'s ``_coverage_for_relative_error()`` for the
    adaptive 90/95/99% coverage rule already used by the offline evaluation
    report.

Documented v0 simplification vs. that offline report: the offline
``compute_conformal_results()`` picks coverage from this KPI's RMSE relative
to the BEST of all 19 candidate models, which requires a full multi-model
benchmark this class doesn't have at loop time (retraining 19 models per
trust-score call would make the batch-sequential loop far too slow, spec.md
§5.3). ``relative_rmse_to_best`` is accepted as an optional constructor arg so
a caller that HAS that benchmark (e.g. from ``evaluation.json``) can still get
adaptive coverage; without it, this defaults to the fixed 90% interval, same
convention as the other two dispatch paths' z_score/Z_90 defaults.

Calibration is internal to fit(): an 80/20 train/calibration split of
whatever (X, y) is passed in (spec.md §5.1's split-conformal, same mechanism
as conformal_predict.py, just computed from one KPI's own data instead of a
model-comparison table). Inputs are standardized internally since several of
the 13 fallback families (SVR, ridge/lasso/elastic_net/bayesian_ridge, KNN,
MLP, GPR base learners inside a stack) are scale-sensitive.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from .base import UncertaintyResult

_NOLHC_SRC = Path(__file__).resolve().parents[4] / "nolhc_ml" / "src"
_EXPERIMENTING_SRC = Path(__file__).resolve().parents[3]
for _p in (_NOLHC_SRC, _EXPERIMENTING_SRC):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from evaluate import _rebuild_estimator  # noqa: E402
from conformal_predict import _coverage_for_relative_error  # noqa: E402

DEFAULT_COVERAGE = 0.90  # matches BaggedTreeJackknife's z_score / GPRNative's Z_90 default


class ConformalFallback:
    """UQEstimator for every model family without a native path (spec.md §5.1)."""

    def __init__(
        self,
        kpi_slug: str,
        registered_as: str,
        base_learners: Optional[List[str]] = None,
        relative_rmse_to_best: Optional[float] = None,
        calibration_frac: float = 0.2,
        random_state: int = 42,
    ) -> None:
        self.kpi_slug = kpi_slug
        self.registered_as = registered_as
        self.base_learners = list(base_learners) if base_learners else []
        self.relative_rmse_to_best = relative_rmse_to_best
        self.calibration_frac = calibration_frac
        self.random_state = random_state

        self._fitted_model = None
        self._scaler: Optional[StandardScaler] = None
        self._q: Optional[float] = None
        self.coverage_level: Optional[float] = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "ConformalFallback":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D (n_samples, n_features), got shape {X.shape}")
        if len(X) != len(y):
            raise ValueError(f"X/y length mismatch: {len(X)} vs {len(y)}")
        min_rows = 10  # need a non-trivial calibration split for the quantile to mean anything
        if len(X) < min_rows:
            raise ValueError(f"need >={min_rows} rows for a train/calibration split, got {len(X)}")

        X_train, X_cal, y_train, y_cal = train_test_split(
            X, y, test_size=self.calibration_frac, random_state=self.random_state
        )

        scaler = StandardScaler().fit(X_train)
        est = _rebuild_estimator(self.registered_as, self.base_learners)
        est.fit(scaler.transform(X_train), y_train)

        residuals = y_cal - est.predict(scaler.transform(X_cal))
        coverage = (
            _coverage_for_relative_error(self.relative_rmse_to_best)
            if self.relative_rmse_to_best is not None
            else DEFAULT_COVERAGE
        )
        q = float(np.quantile(np.abs(residuals), coverage))

        self._scaler = scaler
        self._fitted_model = est
        self.coverage_level = coverage
        self._q = q
        return self

    def predict_with_uncertainty(self, X: np.ndarray) -> UncertaintyResult:
        if self._fitted_model is None or self._scaler is None or self._q is None:
            raise RuntimeError(
                f"ConformalFallback for {self.kpi_slug!r} not fitted -- call fit() first"
            )
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D (n_samples, n_features), got shape {X.shape}")

        mean = self._fitted_model.predict(self._scaler.transform(X))
        lower = mean - self._q
        upper = mean + self._q

        return UncertaintyResult(mean=mean, lower=lower, upper=upper, method="conformal_fallback")
