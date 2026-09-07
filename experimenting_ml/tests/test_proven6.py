"""
Tests for PROVEN_6 / MapieCVPlus (spec.md section 7 item 13, 29-Aug).

Real data throughout -- this wires the actual, benchmarked winning UQ
method per family into usable code, so it's tested the same way as every
other dispatch path: fit + predict against the real 129-row training set,
not mocks.
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

from data import load_xy  # noqa: E402
from loop.proven6 import (  # noqa: E402
    PROVEN_6,
    PROVEN_METHOD,
    PROVEN_REGISTERED_AS_OVERRIDE,
    get_proven_uq_estimator,
)
from loop.uq.dispatch import load_registry  # noqa: E402
from loop.uq.mapie_cv_plus import MapieCVPlus  # noqa: E402


class MapieCVPlusTests(unittest.TestCase):
    def _toy_data(self, n=60, d=5, seed=0):
        rng = np.random.default_rng(seed)
        X = rng.uniform(-2, 2, size=(n, d))
        y = 2.0 * X[:, 0] - X[:, 1] + rng.normal(0, 0.3, size=n)
        return X, y

    def test_unknown_registered_as_raises_at_construction(self):
        with self.assertRaises(KeyError):
            MapieCVPlus(kpi_slug="x", registered_as="not_a_model")

    def test_predict_before_fit_raises(self):
        est = MapieCVPlus(kpi_slug="x", registered_as="elastic_net")
        with self.assertRaises(RuntimeError):
            est.predict_with_uncertainty(np.zeros((2, 5)))

    def test_too_few_rows_for_cv_raises(self):
        est = MapieCVPlus(kpi_slug="x", registered_as="elastic_net", cv=5)
        X, y = self._toy_data(n=3)
        with self.assertRaises(ValueError):
            est.fit(X, y)

    def test_fit_predict_shapes_and_interval_well_formed(self):
        X, y = self._toy_data()
        est = MapieCVPlus(kpi_slug="x", registered_as="elastic_net")
        est.fit(X, y)
        result = est.predict_with_uncertainty(X[:6])
        self.assertEqual(result.mean.shape, (6,))
        self.assertEqual(result.method, "mapie_cv_plus")
        self.assertTrue(np.all(result.lower <= result.mean + 1e-9))
        self.assertTrue(np.all(result.mean <= result.upper + 1e-9))

    def test_works_for_gradient_boosting_without_scaling_flag(self):
        X, y = self._toy_data()
        est = MapieCVPlus(kpi_slug="x", registered_as="gradient_boosting", needs_scaling=False)
        est.fit(X, y)
        result = est.predict_with_uncertainty(X[:4])
        self.assertEqual(result.mean.shape, (4,))


class Proven6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.X_df, cls.Y_df = load_xy()
        cls.registry = load_registry()

    def test_all_six_slugs_covered_by_the_method_table(self):
        self.assertEqual(set(PROVEN_6), set(PROVEN_METHOD))

    def test_unknown_slug_raises(self):
        with self.assertRaises(KeyError):
            get_proven_uq_estimator("not_a_real_kpi", self.registry)

    def test_tt_ib_lb_uses_gradient_boosting_override_not_registered_stacking(self):
        """The one caveat that must never silently disappear: tt_ib_lb's
        real registered winner is 'stacking', but PROVEN_6 deliberately
        tests standalone GradientBoosting there instead (module docstring)."""
        self.assertEqual(self.registry["outputs"]["tt_ib_lb"]["registered_as"], "stacking")
        self.assertEqual(PROVEN_REGISTERED_AS_OVERRIDE["tt_ib_lb"], "gradient_boosting")
        est = get_proven_uq_estimator("tt_ib_lb", self.registry)
        self.assertEqual(est.registered_as, "gradient_boosting")

    def test_each_proven6_estimator_fits_and_predicts_on_real_data(self):
        X = self.X_df.to_numpy(dtype=float)
        for slug in PROVEN_6:
            # raw_key always comes from the real registry -- only registered_as
            # (the model family) is overridden for tt_ib_lb, not the KPI itself.
            raw_key = self.registry["outputs"][slug]["raw_key"]
            y = self.Y_df[raw_key].to_numpy(dtype=float)

            est = get_proven_uq_estimator(slug, self.registry)
            est.fit(X, y)
            result = est.predict_with_uncertainty(X[:5])
            self.assertEqual(result.mean.shape, (5,), msg=f"{slug} failed")
            self.assertTrue(np.all(result.lower <= result.upper + 1e-9), msg=f"{slug} malformed interval")

    def test_wt_ob_lb_uses_conformal_not_native_gpr(self):
        """Real override case: dispatch.py's generic routing would give
        GPRNative for a gpr_matern KPI, but the benchmark's winner was the
        conformal path instead."""
        est = get_proven_uq_estimator("wt_ob_lb", self.registry)
        from loop.uq.conformal_fallback import ConformalFallback

        self.assertIsInstance(est, ConformalFallback)

    def test_tt_ob_lb_matches_dispatch_default(self):
        """Non-override case: ExtraTrees' winning method was the same as
        dispatch.py's own default (native ensemble SD)."""
        est = get_proven_uq_estimator("tt_ob_lb", self.registry)
        from loop.uq.tree_native import BaggedTreeJackknife

        self.assertIsInstance(est, BaggedTreeJackknife)


if __name__ == "__main__":
    unittest.main()
