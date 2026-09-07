"""
T2.1 tests: registry-driven UQ dispatch + the demo-4/stretch-20 KPI scope
(spec.md §5.1, §5.1.1). Covers what T2.1 is responsible for -- routing.
The estimator math itself (T2.3, landed 26-Aug) is tested in its own file,
test_uq_estimators.py -- this file only checks that dispatch.py routes each
KPI to the right CLASS, not that the class computes correct intervals.
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

from loop.kpi_scope import DEMO_4, all_kpi_slugs, resolve_scope  # noqa: E402
from loop.uq.base import UncertaintyResult  # noqa: E402
from loop.uq.conformal_fallback import ConformalFallback  # noqa: E402
from loop.uq.dispatch import (  # noqa: E402
    DispatchPath,
    classify_kpi,
    get_uq_estimator,
    kpis_by_path,
    load_registry,
)
from loop.uq.gpr_native import GPRNative  # noqa: E402
from loop.uq.tree_native import BaggedTreeJackknife  # noqa: E402


class ClassifyKpiTests(unittest.TestCase):
    def test_bagged_tree_models(self):
        self.assertEqual(classify_kpi("random_forest"), DispatchPath.BAGGED_TREE_NATIVE)
        self.assertEqual(classify_kpi("extra_trees"), DispatchPath.BAGGED_TREE_NATIVE)

    def test_gpr_models(self):
        self.assertEqual(classify_kpi("gpr_rbf"), DispatchPath.GPR_NATIVE)
        self.assertEqual(classify_kpi("gpr_matern"), DispatchPath.GPR_NATIVE)

    def test_everything_else_falls_back_to_conformal(self):
        for name in ("stacking", "catboost", "svr_rbf", "ridge", "lasso",
                      "elastic_net", "xgboost", "lightgbm", "knn", "mlp",
                      "adaboost", "unknown_future_model"):
            self.assertEqual(
                classify_kpi(name), DispatchPath.CONFORMAL_FALLBACK,
                f"{name!r} should fall back to conformal, not raise or misroute",
            )

    def test_case_and_whitespace_insensitive(self):
        self.assertEqual(classify_kpi("  Random_Forest  "), DispatchPath.BAGGED_TREE_NATIVE)


class RegistrySplitTests(unittest.TestCase):
    """Confirms the 3/4/13 split quoted in spec.md §5.1.1 against the live registry."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.registry = load_registry()
        except FileNotFoundError as exc:
            raise unittest.SkipTest(f"nolhc_ml registry not built: {exc}")

    def test_registry_has_20_kpis(self):
        self.assertEqual(len(self.registry.get("outputs", {})), 20)

    def test_dispatch_split_matches_spec(self):
        buckets = kpis_by_path(self.registry)
        self.assertEqual(len(buckets[DispatchPath.BAGGED_TREE_NATIVE]), 3)
        self.assertEqual(len(buckets[DispatchPath.GPR_NATIVE]), 4)
        self.assertEqual(len(buckets[DispatchPath.CONFORMAL_FALLBACK]), 13)
        total = sum(len(v) for v in buckets.values())
        self.assertEqual(total, 20)

    def test_demo4_slugs_exist_in_registry(self):
        outputs = self.registry.get("outputs", {})
        for slug in DEMO_4:
            self.assertIn(slug, outputs, f"{slug!r} missing from registry outputs")

    def test_demo4_covers_all_three_paths(self):
        """spec.md §5.1's table: DEMO_4 should exercise all three dispatch paths."""
        paths_hit = {
            classify_kpi(self.registry["outputs"][slug]["registered_as"]) for slug in DEMO_4
        }
        self.assertEqual(
            paths_hit,
            {DispatchPath.BAGGED_TREE_NATIVE, DispatchPath.GPR_NATIVE, DispatchPath.CONFORMAL_FALLBACK},
        )

    def test_all_kpi_slugs_matches_registry_keys(self):
        self.assertEqual(all_kpi_slugs(), sorted(self.registry["outputs"].keys()))


class ResolveScopeTests(unittest.TestCase):
    def test_demo4_scope(self):
        self.assertEqual(resolve_scope("demo4"), DEMO_4)

    def test_unknown_scope_raises(self):
        with self.assertRaises(ValueError):
            resolve_scope("not_a_real_scope")

    def test_all20_scope_matches_registry(self):
        try:
            expected = all_kpi_slugs()
        except FileNotFoundError:
            self.skipTest("nolhc_ml registry not built")
        self.assertEqual(resolve_scope("all20"), expected)
        self.assertEqual(len(expected), 20)


class GetUqEstimatorRoutingTests(unittest.TestCase):
    """The factory routes each DEMO_4 KPI to the right *class*, with real,
    fit-able bodies since T2.3 (26-Aug)."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.registry = load_registry()
        except FileNotFoundError as exc:
            raise unittest.SkipTest(f"nolhc_ml registry not built: {exc}")

    def test_tt_ob_agri_routes_to_bagged_tree(self):
        est = get_uq_estimator("tt_ob_agri", self.registry)
        self.assertIsInstance(est, BaggedTreeJackknife)

    def test_uti_dafm_r_routes_to_gpr_native(self):
        est = get_uq_estimator("uti_dafm_r", self.registry)
        self.assertIsInstance(est, GPRNative)

    def test_wt_ob_a_gb_ross_routes_to_conformal(self):
        est = get_uq_estimator("wt_ob_a_gb_ross", self.registry)
        self.assertIsInstance(est, ConformalFallback)

    def test_tt_ib_dr_routes_to_conformal(self):
        est = get_uq_estimator("tt_ib_dr", self.registry)
        self.assertIsInstance(est, ConformalFallback)

    def test_stacking_kpi_gets_base_learners_and_actually_fits(self):
        """Regression test: get_uq_estimator() used to instantiate
        ConformalFallback for stacking winners WITHOUT passing
        stack_base_learners, so every stacking KPI raised ValueError inside
        fit() despite routing to the "right" class (caught by the T2.3
        real-data smoke test, 26-Aug, on tt_ib_dr). isinstance alone would
        not have caught this -- it has to actually fit."""
        est = get_uq_estimator("tt_ib_dr", self.registry)
        self.assertEqual(
            est.base_learners, self.registry["outputs"]["tt_ib_dr"]["stack_base_learners"]
        )
        rng = np.random.default_rng(0)
        X = rng.uniform(size=(20, 35))
        y = rng.uniform(size=20)
        est.fit(X, y)  # would raise ValueError("Stacking requires >=2 base learners") if unfixed
        result = est.predict_with_uncertainty(X[:3])
        self.assertEqual(result.mean.shape, (3,))

    def test_unknown_kpi_slug_raises_keyerror(self):
        with self.assertRaises(KeyError):
            get_uq_estimator("not_a_real_kpi", self.registry)

    def test_routed_estimator_is_real_not_a_stub(self):
        """T2.3 (26-Aug) replaced the NotImplementedError stubs with real
        fit()/predict_with_uncertainty() bodies -- guard against a future
        regression back to a silently-passing stub by checking the routed
        instance actually produces output, not just that it doesn't raise.
        Estimator correctness itself is test_uq_estimators.py's job; this
        only confirms dispatch.py's routing decision reaches working code."""
        est = get_uq_estimator("tt_ob_agri", self.registry)
        rng = np.random.default_rng(0)
        X = rng.uniform(size=(20, 35))
        y = rng.uniform(size=20)
        est.fit(X, y)
        result = est.predict_with_uncertainty(X[:3])
        self.assertEqual(result.method, "bagged_tree_jackknife")
        self.assertEqual(result.mean.shape, (3,))


class UncertaintyResultTests(unittest.TestCase):
    def test_width_and_normalized_width(self):
        r = UncertaintyResult(
            mean=np.array([1.0, 2.0]),
            lower=np.array([0.5, 1.5]),
            upper=np.array([1.5, 2.5]),
            method="conformal_fallback",
        )
        np.testing.assert_allclose(r.width, [1.0, 1.0])
        np.testing.assert_allclose(r.normalized_width(scale=2.0), [0.5, 0.5])

    def test_shape_mismatch_raises(self):
        with self.assertRaises(ValueError):
            UncertaintyResult(
                mean=np.array([1.0, 2.0]),
                lower=np.array([0.5]),
                upper=np.array([1.5, 2.5]),
                method="conformal_fallback",
            )

    def test_nonpositive_scale_raises(self):
        r = UncertaintyResult(
            mean=np.array([1.0]), lower=np.array([0.5]), upper=np.array([1.5]),
            method="gpr_native",
        )
        with self.assertRaises(ValueError):
            r.normalized_width(scale=0.0)


if __name__ == "__main__":
    unittest.main()
