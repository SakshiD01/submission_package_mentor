"""
Tests for NoveltyScorer (T2.4, spec.md §5.1, §4.1 item 5).

Toy-data tests check the mechanics (shapes, non-negativity, not-fitted
guard); the real-data test reproduces Sakshi's own T2.2 sanity check
(in-hull candidate ~ no novelty penalty, far-out-of-range candidate's
penalty balloons) against the actual 129x35 training set, not a mock.
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

from loop.novelty import NoveltyScorer  # noqa: E402


def _toy_X(n=150, d=5, seed=0):
    rng = np.random.default_rng(seed)
    return rng.normal(0, 1, size=(n, d))


class ValidationTests(unittest.TestCase):
    def test_score_before_fit_raises(self):
        scorer = NoveltyScorer()
        with self.assertRaises(RuntimeError):
            scorer.score(np.zeros((2, 5)))

    def test_too_few_rows_raises(self):
        scorer = NoveltyScorer()
        with self.assertRaises(ValueError):
            scorer.fit(np.zeros((1, 5)))

    def test_wrong_ndim_raises(self):
        scorer = NoveltyScorer()
        with self.assertRaises(ValueError):
            scorer.fit(np.zeros(5))


class ScoreShapeAndSignTests(unittest.TestCase):
    def test_score_shape_and_nonnegative(self):
        X = _toy_X()
        scorer = NoveltyScorer().fit(X)
        scores = scorer.score(X[:10])
        self.assertEqual(scores.shape, (10,))
        self.assertTrue(np.all(scores >= 0.0))

    def test_far_outlier_scores_higher_than_typical_point(self):
        X = _toy_X()
        scorer = NoveltyScorer().fit(X)
        typical = X[0:1]
        far_outlier = np.full((1, X.shape[1]), 50.0)  # way outside a N(0,1) cloud
        s_typical = scorer.score(typical)[0]
        s_outlier = scorer.score(far_outlier)[0]
        self.assertGreater(s_outlier, s_typical)

    def test_reproducible_given_same_random_state(self):
        X = _toy_X()
        s1 = NoveltyScorer(random_state=7).fit(X).score(X[:5])
        s2 = NoveltyScorer(random_state=7).fit(X).score(X[:5])
        np.testing.assert_allclose(s1, s2)


class RealDataSanityCheckTests(unittest.TestCase):
    """Reproduces Sakshi's own T2.2 demo behaviour (spec.md §7's carried-over
    item), but through IsolationForest on the real 35-dim input space
    instead of one KPI's GP posterior std."""

    @classmethod
    def setUpClass(cls):
        from data import load_xy  # noqa: E402

        cls.X_df, _ = load_xy()

    def test_in_sample_point_has_low_novelty(self):
        X = self.X_df.to_numpy(dtype=float)
        scorer = NoveltyScorer().fit(X)
        in_sample_scores = scorer.score(X)
        # most training rows should sit near/at 0 -- they defined the hull
        self.assertLess(np.median(in_sample_scores), 0.05)

    def test_multi_dimensional_ood_candidate_scores_higher(self):
        """A candidate that's extreme across MANY of the 35 inputs at once
        (not just one) is the scenario this score reliably catches -- see
        the sibling test below for the single-dimension case, which it does
        NOT reliably catch at this n=129/d=35 regime (documented in
        novelty.py, not silently tuned around)."""
        X = self.X_df.to_numpy(dtype=float)
        scorer = NoveltyScorer().fit(X)

        x_in_sample = X[0:1]
        x_ood = X.max(axis=0, keepdims=True) * 3.0  # every input pushed to 3x its observed max

        s_in = scorer.score(x_in_sample)[0]
        s_ood = scorer.score(x_ood)[0]
        self.assertGreater(s_ood, s_in)
        self.assertGreater(s_ood, 0.0)

    def test_single_dimension_extreme_not_reliably_flagged(self):
        """Documents a real, measured limitation (27-Aug): pushing just ONE
        of the 35 inputs to even 20x its observed max does not move the
        score off 0 -- IsolationForest's axis-aligned splits dilute a single
        extreme dimension across the other 34 unremarkable ones. This is the
        opposite of the GP ground-truth's gp_std (test_ground_truth_gp.py),
        which balloons for exactly this kind of single-input perturbation --
        a genuine disagreement between the two novelty signals, not a bug in
        either. Guards against a future "helpful" hyperparameter tweak
        quietly hiding this rather than it being a documented, known trait."""
        X = self.X_df.to_numpy(dtype=float)
        scorer = NoveltyScorer().fit(X)

        x_extreme_one_dim = X[0:1].copy()
        x_extreme_one_dim[0, 0] = X[:, 0].max() * 20.0

        self.assertEqual(scorer.score(x_extreme_one_dim)[0], 0.0)


if __name__ == "__main__":
    unittest.main()
