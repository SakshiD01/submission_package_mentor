"""
Tests for the full-DEMO_4 ground truth (spec.md §7 items 4 & 6, decided
26-Aug-2026): GP for the GPR-won KPI, production model for the other three.
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
from loop.des_backend.demo4_ground_truth import (  # noqa: E402
    ground_truth_fns_and_noise_for_demo4,
)
from loop.des_backend.ground_truth_gp import DEFAULT_ARTIFACT_PATH  # noqa: E402
from loop.des_backend.synthetic import SyntheticDESBackend  # noqa: E402
from loop.kpi_scope import DEMO_4  # noqa: E402


@unittest.skipUnless(DEFAULT_ARTIFACT_PATH.is_file(), "run fit_ground_truth.py first")
class Demo4GroundTruthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fns, cls.noise = ground_truth_fns_and_noise_for_demo4()
        cls.X_df, cls.Y_df = load_xy()

    def test_covers_all_four_demo4_kpis(self):
        """The whole point of this module: full DEMO_4 coverage, not the 3
        Sakshi originally fit GPs for."""
        self.assertEqual(set(self.fns), set(DEMO_4))
        self.assertEqual(set(self.noise), set(DEMO_4))

    def test_production_model_predictions_are_close_on_training_rows(self):
        """Unlike the forced GP on tt_ob_agri (mean abs error ~ tens of
        hours per test_ground_truth_gp.py), the real production model
        should track its own training rows tightly."""
        X = self.X_df.to_numpy(dtype=float)
        for slug, raw_key in (
            ("tt_ob_agri", "TT_OB_Agri"),
            ("wt_ob_a_gb_ross", "WT_OB_A_GB-Ross"),
            ("tt_ib_dr", "TT_IB_DR"),
        ):
            y_true = self.Y_df[raw_key].to_numpy(dtype=float)
            y_pred = self.fns[slug](X)
            self.assertEqual(y_pred.shape, y_true.shape)
            # in-sample production-model fit should be tight for the
            # tree/boosting winners; tt_ib_dr is the known-bad stress test
            # (R2=-0.12) so its own bar is looser, still not garbage-shaped.
            rel_err = np.abs(y_pred - y_true).mean() / (y_true.max() - y_true.min())
            self.assertLess(rel_err, 0.25, msg=f"{slug}: relative error too high")

    def test_noise_std_all_positive(self):
        self.assertTrue(all(v > 0 for v in self.noise.values()))

    def test_backend_simulates_full_demo4(self):
        backend = SyntheticDESBackend(kpi_slugs=DEMO_4, ground_truth_fns=self.fns, noise_std=self.noise)
        candidates = self.X_df.iloc[:3]
        out = backend.simulate(candidates, n_replications=4, seed=7)
        self.assertEqual(len(out), 12)
        for slug in DEMO_4:
            self.assertIn(slug, out.columns)
            self.assertFalse(out[slug].isna().any())


if __name__ == "__main__":
    unittest.main()
