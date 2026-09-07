"""
Tests for the T2.2 ground-truth GP artifact + its adapter into
SyntheticDESBackend (spec.md §5.2, ground_truth_gp.py).

Uses the real fitted artifact (fit_ground_truth.py's output), not a mock --
this is checking that Sakshi's T2.2 deliverable actually integrates, not
just that the adapter's plumbing is shaped right.
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
import pandas as pd  # noqa: E402

from data import load_xy  # noqa: E402
from loop.des_backend.ground_truth_gp import (  # noqa: E402
    DEFAULT_ARTIFACT_PATH,
    ground_truth_fns_and_noise,
    load_ground_truth_artifact,
)
from loop.des_backend.synthetic import SyntheticDESBackend  # noqa: E402


@unittest.skipUnless(DEFAULT_ARTIFACT_PATH.is_file(), "run fit_ground_truth.py first")
class GroundTruthArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.art = load_ground_truth_artifact()
        cls.X_df, cls.Y_df = load_xy()

    def test_covers_expected_kpis(self):
        """Documents the current scope gap (spec.md §7): T2.2 fit 3 KPIs,
        only 2 of which are in DEMO_4 -- this is not the full demo-4 set."""
        self.assertEqual(set(self.art["kpis"]), {"TT_OB_Agri", "TT_IB_LB", "Uti_DAFM_R"})

    def test_in_sample_prediction_close_to_recorded_value(self):
        """Sanity check matching Sakshi's own demo: an in-sample row's GP
        posterior mean should land close to what was actually recorded,
        not an arbitrary number."""
        fns, _ = ground_truth_fns_and_noise(self.art)
        X = self.X_df.to_numpy(dtype=float)
        y_true = self.Y_df["TT_OB_Agri"].to_numpy(dtype=float)
        y_pred = fns["tt_ob_agri"](X)
        # tree-won KPI forced through a smooth GP -- not exact, but should be
        # in the right ballpark relative to the KPI's own range (169-2.5=166.5)
        self.assertLess(np.abs(y_pred - y_true).mean(), 20.0)

    def test_ood_candidate_inflates_gp_epistemic_std(self):
        """Reproduces Sakshi's reported sanity behaviour (spec doc §6): an
        input pushed far outside its observed range should get a much wider
        GP posterior std than an in-sample point -- the exact signal T2.4's
        novelty scorer is meant to consume."""
        art = self.art
        gp = art["kpis"]["TT_IB_LB"]["gp"]
        scaler = art["scaler"]
        X = self.X_df.to_numpy(dtype=float)

        x_in_sample = X[0:1]
        x_ood = X[0:1].copy()
        x_ood[0, 0] = X[:, 0].max() * 3.0

        _, std_in = gp.predict(scaler.transform(x_in_sample), return_std=True)
        _, std_ood = gp.predict(scaler.transform(x_ood), return_std=True)
        self.assertGreater(std_ood[0], std_in[0] * 2)


@unittest.skipUnless(DEFAULT_ARTIFACT_PATH.is_file(), "run fit_ground_truth.py first")
class SyntheticDESBackendIntegrationTests(unittest.TestCase):
    """Confirms T2.2's real GP fits (not toy ground truth) plug straight into
    T2.5's SyntheticDESBackend through this adapter -- the seam both sides
    were built against, now closed with real data."""

    def test_backend_simulates_with_real_gp_ground_truth(self):
        fns, noise = ground_truth_fns_and_noise()
        kpis = list(fns)  # {tt_ob_agri, tt_ib_lb, uti_dafm_r} -- see scope-gap test above
        backend = SyntheticDESBackend(kpi_slugs=kpis, ground_truth_fns=fns, noise_std=noise)

        X_df, _ = load_xy()
        candidates = X_df.iloc[:3]
        out = backend.simulate(candidates, n_replications=5, seed=1)

        self.assertEqual(len(out), 15)  # 3 candidates x 5 replications
        for kpi in kpis:
            self.assertIn(kpi, out.columns)
            self.assertFalse(out[kpi].isna().any())


if __name__ == "__main__":
    unittest.main()
