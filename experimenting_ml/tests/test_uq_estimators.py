"""
T2.3 tests: the real fit()/predict_with_uncertainty() bodies for all three
UQEstimator dispatch paths (spec.md §5.1, 26-27 Aug 2026).

Fixed random seeds throughout, synthetic linear-ish ground truth with known
noise -- these tests check the MECHANICS (shapes, monotonic interval widths,
not-fitted guards, reproducibility) not whether a specific model family beats
another on real NOLHC data. Real-data validation is T2.8's smoke test.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np  # noqa: E402

from loop.uq.conformal_fallback import ConformalFallback  # noqa: E402
from loop.uq.gpr_native import GPRNative  # noqa: E402
from loop.uq.tree_native import BaggedTreeJackknife  # noqa: E402


def _toy_data(n=40, d=5, noise=0.5, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.uniform(-2, 2, size=(n, d))
    y = 3.0 * X[:, 0] - X[:, 1] + rng.normal(0, noise, size=n)
    return X, y


class BaggedTreeJackknifeTests(unittest.TestCase):
    def test_unknown_registered_as_raises_at_construction(self):
        with self.assertRaises(KeyError):
            BaggedTreeJackknife(kpi_slug="x", registered_as="not_a_model")

    def test_predict_before_fit_raises(self):
        est = BaggedTreeJackknife(kpi_slug="tt_ob_agri", registered_as="random_forest")
        with self.assertRaises(RuntimeError):
            est.predict_with_uncertainty(np.zeros((2, 5)))

    def test_fit_predict_shapes_and_method_tag(self):
        X, y = _toy_data()
        est = BaggedTreeJackknife(kpi_slug="tt_ob_agri", registered_as="random_forest")
        est.fit(X, y)
        result = est.predict_with_uncertainty(X[:5])
        self.assertEqual(result.mean.shape, (5,))
        self.assertEqual(result.lower.shape, (5,))
        self.assertEqual(result.upper.shape, (5,))
        self.assertEqual(result.method, "bagged_tree_jackknife")

    def test_interval_is_well_formed(self):
        """lower <= mean <= upper for every row -- the one invariant every
        dispatch path must satisfy regardless of how its width is computed."""
        X, y = _toy_data()
        est = BaggedTreeJackknife(kpi_slug="tt_ob_agri", registered_as="extra_trees")
        est.fit(X, y)
        result = est.predict_with_uncertainty(X)
        self.assertTrue(np.all(result.lower <= result.mean + 1e-9))
        self.assertTrue(np.all(result.mean <= result.upper + 1e-9))

    def test_x_y_length_mismatch_raises(self):
        est = BaggedTreeJackknife(kpi_slug="x", registered_as="random_forest")
        with self.assertRaises(ValueError):
            est.fit(np.zeros((5, 3)), np.zeros(4))


class GPRNativeTests(unittest.TestCase):
    def test_non_gpr_registered_as_raises_at_construction(self):
        with self.assertRaises(KeyError):
            GPRNative(kpi_slug="x", registered_as="random_forest")

    def test_predict_before_fit_raises(self):
        est = GPRNative(kpi_slug="uti_dafm_r", registered_as="gpr_rbf")
        with self.assertRaises(RuntimeError):
            est.predict_with_uncertainty(np.zeros((2, 5)))

    def test_fit_predict_shapes_and_method_tag(self):
        X, y = _toy_data(n=25)
        est = GPRNative(kpi_slug="uti_dafm_r", registered_as="gpr_rbf")
        est.fit(X, y)
        result = est.predict_with_uncertainty(X[:4])
        self.assertEqual(result.mean.shape, (4,))
        self.assertEqual(result.method, "gpr_native")

    def test_interval_is_well_formed(self):
        X, y = _toy_data(n=25)
        est = GPRNative(kpi_slug="uti_dafm_r", registered_as="gpr_matern")
        est.fit(X, y)
        result = est.predict_with_uncertainty(X)
        self.assertTrue(np.all(result.lower <= result.mean + 1e-9))
        self.assertTrue(np.all(result.mean <= result.upper + 1e-9))

    def test_uses_exact_z90_from_evaluate_module(self):
        """Guards against silently drifting from evaluate.py's Z_90 constant
        (spec.md's whole point: reuse, not re-derive)."""
        from evaluate import Z_90  # same import path gpr_native.py itself uses

        X, y = _toy_data(n=25)
        est = GPRNative(kpi_slug="uti_dafm_r", registered_as="gpr_rbf")
        est.fit(X, y)
        result = est.predict_with_uncertainty(X[:3])
        # half-width / std should equal Z_90 exactly (up to float error)
        _, std = est._fitted_model.predict(est._scaler.transform(X[:3]), return_std=True)
        half_width = (result.upper - result.mean)
        np.testing.assert_allclose(half_width, Z_90 * std, rtol=1e-6)


class ConformalFallbackTests(unittest.TestCase):
    def test_predict_before_fit_raises(self):
        est = ConformalFallback(kpi_slug="tt_ib_dr", registered_as="knn")
        with self.assertRaises(RuntimeError):
            est.predict_with_uncertainty(np.zeros((2, 5)))

    def test_too_few_rows_raises(self):
        est = ConformalFallback(kpi_slug="x", registered_as="ridge")
        X, y = _toy_data(n=5)
        with self.assertRaises(ValueError):
            est.fit(X, y)

    def test_fit_predict_shapes_and_method_tag(self):
        X, y = _toy_data(n=60)
        est = ConformalFallback(kpi_slug="x", registered_as="ridge")
        est.fit(X, y)
        result = est.predict_with_uncertainty(X[:6])
        self.assertEqual(result.mean.shape, (6,))
        self.assertEqual(result.method, "conformal_fallback")
        self.assertEqual(est.coverage_level, 0.90)  # default, no relative_rmse_to_best given

    def test_interval_is_well_formed(self):
        X, y = _toy_data(n=60)
        est = ConformalFallback(kpi_slug="x", registered_as="knn")
        est.fit(X, y)
        result = est.predict_with_uncertainty(X)
        self.assertTrue(np.all(result.lower <= result.mean + 1e-9))
        self.assertTrue(np.all(result.mean <= result.upper + 1e-9))

    def test_stacking_winner_builds_via_rebuild_estimator(self):
        """The 13-of-20 fallback bucket includes stacking winners -- this is
        the one path that needs base_learners wired through correctly."""
        X, y = _toy_data(n=60)
        est = ConformalFallback(
            kpi_slug="tt_ib_agri",
            registered_as="stacking",
            base_learners=["extra_trees", "ridge", "knn"],
        )
        est.fit(X, y)
        result = est.predict_with_uncertainty(X[:5])
        self.assertEqual(result.mean.shape, (5,))

    def test_relative_rmse_to_best_changes_coverage(self):
        """Optional adaptive-coverage path (spec.md's documented v0
        simplification): a caller that supplies relative_rmse_to_best should
        get a coverage level != the fixed 0.90 default when the model is
        clearly worse than the field's best."""
        X, y = _toy_data(n=60)
        est = ConformalFallback(kpi_slug="x", registered_as="ridge", relative_rmse_to_best=1.5)
        est.fit(X, y)
        self.assertEqual(est.coverage_level, 0.99)  # >1.20 relative RMSE -> 99% per conformal_predict.py

    def test_reproducible_given_same_random_state(self):
        X, y = _toy_data(n=60)
        est1 = ConformalFallback(kpi_slug="x", registered_as="ridge", random_state=7)
        est2 = ConformalFallback(kpi_slug="x", registered_as="ridge", random_state=7)
        est1.fit(X, y)
        est2.fit(X, y)
        self.assertAlmostEqual(est1._q, est2._q)


if __name__ == "__main__":
    unittest.main()
