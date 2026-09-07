"""
Tests for trust.py (spec.md §5.1, §7 item 3 -- mentor-confirmed per-KPI
threshold calibration + any-KPI-trips flagging rule, 25-Aug-2026).
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

from loop.trust import (  # noqa: E402
    calibrate_threshold_global,
    calibrate_thresholds_per_kpi,
    decide,
    trust_score,
)


class TrustScoreTests(unittest.TestCase):
    def test_sums_terms(self):
        self.assertAlmostEqual(trust_score(0.3, 0.2), 0.5)

    def test_zero_is_valid(self):
        self.assertAlmostEqual(trust_score(0.0, 0.0), 0.0)

    def test_negative_uq_term_raises(self):
        with self.assertRaises(ValueError):
            trust_score(-0.1, 0.2)

    def test_negative_novelty_term_raises(self):
        with self.assertRaises(ValueError):
            trust_score(0.1, -0.2)


class CalibrationTests(unittest.TestCase):
    def test_per_kpi_thresholds_are_independent(self):
        """The whole reason per-KPI calibration is the mentor's working
        default: two KPIs on very different scales get very different
        thresholds from the same quantile rule."""
        scores = {
            "wt_ib_a_dub": np.array([0.01, 0.02, 0.03, 0.04, 0.50]),  # hours, small scale
            "tt_ob_lb": np.array([1.0, 2.0, 3.0, 4.0, 50.0]),          # hours, large scale
        }
        thresholds = calibrate_thresholds_per_kpi(scores, quantile=0.8)
        self.assertLess(thresholds["wt_ib_a_dub"], thresholds["tt_ob_lb"])
        # 80th percentile of [0.01,0.02,0.03,0.04,0.50] via numpy linear interp
        self.assertAlmostEqual(thresholds["wt_ib_a_dub"], float(np.quantile(scores["wt_ib_a_dub"], 0.8)))

    def test_invalid_quantile_raises(self):
        with self.assertRaises(ValueError):
            calibrate_thresholds_per_kpi({"a": np.array([1.0, 2.0])}, quantile=1.5)
        with self.assertRaises(ValueError):
            calibrate_threshold_global({"a": np.array([1.0, 2.0])}, quantile=0.0)

    def test_global_threshold_pools_across_kpis(self):
        scores = {
            "a": np.array([1.0, 1.0, 1.0, 1.0]),
            "b": np.array([100.0, 100.0, 100.0, 100.0]),
        }
        pooled = calibrate_threshold_global(scores, quantile=0.5)
        # median of [1,1,1,1,100,100,100,100] -- pooling means the small-scale
        # KPI's threshold gets swamped by the large-scale one (the failure
        # mode per-KPI calibration exists to avoid).
        self.assertGreater(pooled, 1.0)

    def test_empty_calibration_scores_raises(self):
        with self.assertRaises(ValueError):
            calibrate_threshold_global({})


class DecideTests(unittest.TestCase):
    def test_not_flagged_when_all_kpis_within_threshold(self):
        d = decide(
            per_kpi_trust_score={"kpi_a": 0.2, "kpi_b": 0.3},
            thresholds={"kpi_a": 0.5, "kpi_b": 0.5},
        )
        self.assertFalse(d.flagged)
        self.assertEqual(d.tripped_kpis, [])

    def test_flagged_if_any_single_kpi_exceeds_its_threshold(self):
        """Mentor's decision rule (spec.md §7 item 3): flag if ANY KPI falls
        below its threshold -- one shared criterion, per-KPI calibration."""
        d = decide(
            per_kpi_trust_score={"kpi_a": 0.2, "kpi_b": 0.9},
            thresholds={"kpi_a": 0.5, "kpi_b": 0.5},
        )
        self.assertTrue(d.flagged)
        self.assertEqual(d.tripped_kpis, ["kpi_b"])

    def test_flagged_when_all_kpis_exceed(self):
        d = decide(
            per_kpi_trust_score={"kpi_a": 0.9, "kpi_b": 0.9},
            thresholds={"kpi_a": 0.5, "kpi_b": 0.5},
        )
        self.assertTrue(d.flagged)
        self.assertEqual(set(d.tripped_kpis), {"kpi_a", "kpi_b"})

    def test_exactly_at_threshold_does_not_trip(self):
        """Boundary: '> threshold' not '>= threshold', so calibrating at the
        90th percentile flags ~10% of calibration points, not more."""
        d = decide(per_kpi_trust_score={"kpi_a": 0.5}, thresholds={"kpi_a": 0.5})
        self.assertFalse(d.flagged)

    def test_missing_threshold_raises_keyerror(self):
        with self.assertRaises(KeyError):
            decide(per_kpi_trust_score={"kpi_a": 0.2, "kpi_c": 0.1}, thresholds={"kpi_a": 0.5})


if __name__ == "__main__":
    unittest.main()
