"""
Bagged-tree native UQ: variance across a fitted RandomForest/ExtraTrees'
``estimators_`` predictions (spec.md §5.1's bagging-variance proxy for the
infinitesimal jackknife -- a documented v0 simplification, not the full
Wager/Hastie/Efron bias-corrected jackknife; see spec.md §4.1 item 1).

Covers 3 of 20 registered KPIs (TT_OB_Agri, TT_OB_LB, TT_OB_DR) -- the only
dispatch path that is genuinely new code, not a reuse of existing pipeline logic.

T2.3 (26-27 Aug 2026, spec.md §6): real fit()/predict_with_uncertainty(), no
longer a stub. Reuses the exact hyperparameters ``registered_as`` was trained
with, via ``nolhc_ml/src/candidate_models.CANDIDATE_MODELS`` -- this is the
same architecture registry.json's winner was chosen from, not a re-guess.
No scaling: tree splits are invariant to monotone feature transforms, so
RF/ExtraTrees are fit on raw X (unlike GPRNative/ConformalFallback).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.base import clone

from .base import UncertaintyResult

_NOLHC_SRC = Path(__file__).resolve().parents[4] / "nolhc_ml" / "src"
if str(_NOLHC_SRC) not in sys.path:
    sys.path.insert(0, str(_NOLHC_SRC))

from candidate_models import CANDIDATE_MODELS  # noqa: E402


class BaggedTreeJackknife:
    """UQEstimator for RandomForest/ExtraTrees winners (spec.md §5.1 tier: bagged-tree native)."""

    def __init__(self, kpi_slug: str, registered_as: str, z_score: float = 1.645) -> None:
        if registered_as not in CANDIDATE_MODELS:
            raise KeyError(
                f"{registered_as!r} not a known candidate model for {kpi_slug!r}: "
                f"{sorted(CANDIDATE_MODELS)}"
            )
        self.kpi_slug = kpi_slug
        self.registered_as = registered_as
        self.z_score = z_score  # 90% interval, matching the existing conformal default
        self._fitted_model = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "BaggedTreeJackknife":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D (n_samples, n_features), got shape {X.shape}")
        if len(X) != len(y):
            raise ValueError(f"X/y length mismatch: {len(X)} vs {len(y)}")
        if len(X) < 2:
            raise ValueError(f"need >=2 rows to fit, got {len(X)}")

        est = clone(CANDIDATE_MODELS[self.registered_as])
        est.fit(X, y)
        self._fitted_model = est
        return self

    def predict_with_uncertainty(self, X: np.ndarray) -> UncertaintyResult:
        if self._fitted_model is None:
            raise RuntimeError(
                f"BaggedTreeJackknife for {self.kpi_slug!r} not fitted -- call fit() first"
            )
        X = np.asarray(X, dtype=float)
        if X.ndim != 2:
            raise ValueError(f"X must be 2D (n_samples, n_features), got shape {X.shape}")

        # Bagging-variance proxy: spread across the ensemble's individual
        # trees, not a single point estimate's confidence -- this is what
        # makes it a per-row UNCERTAINTY signal rather than just a prediction.
        tree_preds = np.stack(
            [tree.predict(X) for tree in self._fitted_model.estimators_], axis=0
        )  # (n_trees, n_rows)
        mean = tree_preds.mean(axis=0)
        std = tree_preds.std(axis=0, ddof=1) if tree_preds.shape[0] > 1 else np.zeros_like(mean)
        half_width = self.z_score * std

        return UncertaintyResult(
            mean=mean,
            lower=mean - half_width,
            upper=mean + half_width,
            method="bagged_tree_jackknife",
        )
