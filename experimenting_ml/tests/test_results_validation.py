"""
Tests for results_validation.py (T2.13, spec.md section 7 item 15).

The main test reproduces the exact 5-Sep incident (4 KPIs reading exactly
0.000 across a whole real batch) against real historical data, to prove
this check would have caught it immediately rather than requiring manual
cross-referencing against the historical range by hand.
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
from loop.results_validation import validate_results  # noqa: E402
from loop.uq.dispatch import load_registry  # noqa: E402


class ValidateResultsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.X_df, cls.Y_df = load_xy()
        cls.registry = load_registry()

    def test_clean_batch_produces_no_warnings(self):
        """Sampling real historical values back at the historical KPIs
        should not trip either check -- a negative control."""
        results = pd.DataFrame({
            "run_id": ["r1", "r1", "r2", "r2"],
            "replication": [1, 2, 1, 2],
            "seed": [1, 2, 3, 4],
            "tt_ob_agri": [self.Y_df["TT_OB_Agri"].iloc[0], self.Y_df["TT_OB_Agri"].iloc[1],
                            self.Y_df["TT_OB_Agri"].iloc[2], self.Y_df["TT_OB_Agri"].iloc[3]],
        })
        warnings = validate_results(results, self.Y_df, self.registry)
        self.assertEqual(warnings, [])

    def test_reproduces_the_5_sep_incident(self):
        """The real case: 4 KPIs read exactly 0.000 across a whole 10-candidate
        batch, while their historical range is clearly nonzero. This check
        must flag all 4 -- it's the check that should have caught this
        before it required manual cross-referencing."""
        n = 10
        results = pd.DataFrame({
            "run_id": [f"proposed_{i:04d}" for i in range(n)],
            "replication": [1] * n,
            "seed": [1] * n,
            "wt_ob_a_gb_dub": [0.0] * n,
            "wt_ob_a_gb_ross": [0.0] * n,
            "wt_ob_na_gb_dub": [0.0] * n,
            "wt_ob_na_gb_ross": [0.0] * n,
            "tt_ob_agri": [14.0 + 0.1 * i for i in range(n)],  # plausible, varying -- should NOT be flagged
        })
        warnings = validate_results(results, self.Y_df, self.registry)
        flagged_slugs = set()
        for w in warnings:
            for slug in ["wt_ob_a_gb_dub", "wt_ob_a_gb_ross", "wt_ob_na_gb_dub", "wt_ob_na_gb_ross"]:
                if w.startswith(slug + " "):
                    flagged_slugs.add(slug)
        self.assertEqual(flagged_slugs, {"wt_ob_a_gb_dub", "wt_ob_a_gb_ross", "wt_ob_na_gb_dub", "wt_ob_na_gb_ross"})
        self.assertFalse(any(w.startswith("tt_ob_agri ") for w in warnings))

    def test_out_of_range_value_flagged(self):
        hist = self.Y_df["TT_OB_Agri"].to_numpy(dtype=float)
        wildly_high = hist.max() * 5  # far beyond any plausible historical extrapolation
        results = pd.DataFrame({
            "run_id": ["r1"], "replication": [1], "seed": [1],
            "tt_ob_agri": [wildly_high],
        })
        warnings = validate_results(results, self.Y_df, self.registry)
        self.assertTrue(any(w.startswith("tt_ob_agri ") for w in warnings))

    def test_single_replication_identical_value_not_flagged(self):
        """A single value can't be 'suspiciously constant' -- needs >1 to compare."""
        results = pd.DataFrame({
            "run_id": ["r1"], "replication": [1], "seed": [1],
            "tt_ob_agri": [float(self.Y_df["TT_OB_Agri"].iloc[0])],
        })
        warnings = validate_results(results, self.Y_df, self.registry)
        self.assertEqual(warnings, [])

    def test_unknown_slug_ignored_not_crashed(self):
        results = pd.DataFrame({
            "run_id": ["r1"], "replication": [1], "seed": [1],
            "not_a_real_kpi": [1.0],
        })
        warnings = validate_results(results, self.Y_df, self.registry)
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
