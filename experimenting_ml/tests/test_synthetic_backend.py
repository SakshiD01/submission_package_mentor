"""
Tests for SyntheticDESBackend (spec.md §5.2, §7 item 2 -- mentor-confirmed
replication-level output, 25-Aug-2026). Ground truth / noise are injected
mocks here -- T2.2's actual GP fits land separately; this file tests the
sampling mechanics only.
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

from loop.des_backend.synthetic import SyntheticDESBackend  # noqa: E402


def _constant_gt(value: float):
    return lambda X: np.full(X.shape[0], value)


def _make_backend(noise_std=None):
    kpis = ["kpi_a", "kpi_b"]
    gt = {"kpi_a": _constant_gt(10.0), "kpi_b": _constant_gt(0.5)}
    noise = noise_std or {"kpi_a": 1.0, "kpi_b": 0.05}
    return SyntheticDESBackend(kpi_slugs=kpis, ground_truth_fns=gt, noise_std=noise)


def _candidates(n=3):
    return pd.DataFrame(
        np.random.default_rng(0).uniform(size=(n, 35)),
        index=[f"cand_{i}" for i in range(n)],
    )


class ShapeTests(unittest.TestCase):
    def test_one_row_per_candidate_times_replication(self):
        backend = _make_backend()
        out = backend.simulate(_candidates(3), n_replications=4, seed=1)
        self.assertEqual(len(out), 12)

    def test_columns_match_manual_worklist_import_contract(self):
        """spec.md §7 item 2: run_id, replication, seed, then one KPI column each."""
        backend = _make_backend()
        out = backend.simulate(_candidates(2), n_replications=2, seed=1)
        self.assertEqual(list(out.columns), ["run_id", "replication", "seed", "kpi_a", "kpi_b"])

    def test_run_id_comes_from_candidate_index(self):
        backend = _make_backend()
        out = backend.simulate(_candidates(2), n_replications=3, seed=1)
        self.assertEqual(set(out["run_id"]), {"cand_0", "cand_1"})
        self.assertEqual(list(out[out["run_id"] == "cand_0"]["replication"]), [1, 2, 3])


class NoiseAndReproducibilityTests(unittest.TestCase):
    def test_zero_noise_is_deterministic_ground_truth(self):
        backend = _make_backend(noise_std={"kpi_a": 0.0, "kpi_b": 0.0})
        out = backend.simulate(_candidates(1), n_replications=5, seed=1)
        self.assertTrue((out["kpi_a"] == 10.0).all())
        self.assertTrue((out["kpi_b"] == 0.5).all())

    def test_same_seed_is_reproducible(self):
        backend = _make_backend()
        out1 = backend.simulate(_candidates(2), n_replications=3, seed=42)
        out2 = backend.simulate(_candidates(2), n_replications=3, seed=42)
        pd.testing.assert_frame_equal(out1, out2)

    def test_different_seeds_differ(self):
        backend = _make_backend()
        out1 = backend.simulate(_candidates(2), n_replications=3, seed=42)
        out2 = backend.simulate(_candidates(2), n_replications=3, seed=43)
        self.assertFalse(out1["kpi_a"].equals(out2["kpi_a"]))

    def test_replications_within_one_run_are_not_identical(self):
        """Guards against a seeding bug where every replication of the same
        candidate accidentally draws the same noise (spec §7 item 2's whole
        point is separating replication-level DES noise)."""
        backend = _make_backend()
        out = backend.simulate(_candidates(1), n_replications=5, seed=7)
        self.assertGreater(out["kpi_a"].nunique(), 1)


class ValidationTests(unittest.TestCase):
    def test_missing_ground_truth_fn_raises(self):
        with self.assertRaises(KeyError):
            SyntheticDESBackend(
                kpi_slugs=["kpi_a", "kpi_b"],
                ground_truth_fns={"kpi_a": _constant_gt(1.0)},
                noise_std={"kpi_a": 1.0, "kpi_b": 1.0},
            )

    def test_missing_noise_std_raises(self):
        with self.assertRaises(KeyError):
            SyntheticDESBackend(
                kpi_slugs=["kpi_a", "kpi_b"],
                ground_truth_fns={"kpi_a": _constant_gt(1.0), "kpi_b": _constant_gt(1.0)},
                noise_std={"kpi_a": 1.0},
            )

    def test_negative_noise_std_raises(self):
        with self.assertRaises(ValueError):
            SyntheticDESBackend(
                kpi_slugs=["kpi_a"],
                ground_truth_fns={"kpi_a": _constant_gt(1.0)},
                noise_std={"kpi_a": -1.0},
            )

    def test_n_replications_below_one_raises(self):
        backend = _make_backend()
        with self.assertRaises(ValueError):
            backend.simulate(_candidates(1), n_replications=0, seed=1)

    def test_empty_candidates_raises(self):
        backend = _make_backend()
        with self.assertRaises(ValueError):
            backend.simulate(_candidates(0), n_replications=1, seed=1)


if __name__ == "__main__":
    unittest.main()
