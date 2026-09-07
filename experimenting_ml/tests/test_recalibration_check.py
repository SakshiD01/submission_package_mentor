"""
Tests for recalibration_check.py (spec.md §9 follow-up, 5-Sep).

The main test locks in the exact validation that caught a real bug while
building this: the first version used this repo's own
splits.train_test_indices() for the outer 80/20 split and got numbers that
did NOT match UQ_Method_Benchmark.xlsx at all (84.6%/65.4% vs. the
workbook's real 96.2%/92.3% for wt_ob_lb's native/conformal GPR) -- even
though wt_ob_lb's training data hasn't grown since the original benchmark
(WT_OB_LB has no known AnyLogic field, spec.md item 5/17). Switching the
split to sklearn's own train_test_split(test_size=0.2, random_state=42)
reproduced the workbook exactly. This test is what would catch a
regression back to the wrong split mechanism.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from loop.proven6 import PROVEN_6  # noqa: E402
from loop.recalibration_check import run_recalibration_check  # noqa: E402
from loop.uq.dispatch import load_registry  # noqa: E402


class RecalibrationCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry()
        cls.checks = run_recalibration_check(cls.registry)

    def test_one_check_per_proven6_kpi(self):
        self.assertEqual({c.kpi_slug for c in self.checks}, set(PROVEN_6))

    def test_wt_ob_lb_reproduces_the_committed_benchmark_workbook(self):
        """wt_ob_lb's 129 rows are unchanged since the 1-Sep benchmark
        (no real AnyLogic Cloud round has ever populated WT_OB_LB) -- so
        this check's numbers on it must match UQ_Method_Benchmark.xlsx's
        'gpr_matern' sheet, to 2 decimal places on coverage and 3 on width.
        A mismatch here means the split mechanism has drifted again, not
        that anything about the KPI itself has changed."""
        check = next(c for c in self.checks if c.kpi_slug == "wt_ob_lb")
        self.assertEqual(check.n_train, 103)
        self.assertEqual(check.n_test, 26)

        by_method = {r.method: r for r in check.results}
        self.assertAlmostEqual(by_method["gpr_native"].coverage, 0.962, places=2)
        self.assertAlmostEqual(by_method["gpr_native"].mean_width, 0.7055, places=3)
        self.assertAlmostEqual(by_method["conformal_fallback"].coverage, 0.923, places=2)
        self.assertAlmostEqual(by_method["conformal_fallback"].mean_width, 0.7061, places=3)

        # The workbook's own conclusion: conformalized GPR (split conformal)
        # closest to the 90% target, native SD a safe second -- must still
        # be what this check recommends, since nothing about this KPI's
        # data has changed to justify a different answer.
        self.assertEqual(check.recommended_method, "conformal_fallback")
        self.assertFalse(check.changed)

    def test_grown_kpis_have_more_than_129_rows(self):
        """Sanity check on the dataset-growth bookkeeping itself: KPIs that
        DID get real values from both ingested manual rounds should show
        n_train + n_test > 129 (the original dataset alone)."""
        grown = {"tt_ob_lb", "uti_cus_r", "wt_ib_na_ross", "tt_ib_lb"}
        for check in self.checks:
            if check.kpi_slug in grown:
                self.assertGreater(check.n_train + check.n_test, 129, check.kpi_slug)

    def test_recommended_method_is_always_one_of_the_tested_methods(self):
        for check in self.checks:
            self.assertIn(check.recommended_method, {r.method for r in check.results})
            self.assertEqual(check.changed, check.recommended_method != check.current_method)


if __name__ == "__main__":
    unittest.main()
