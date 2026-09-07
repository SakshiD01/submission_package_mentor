"""
Tests for T2.7's loop orchestrator (loop.py) -- spec.md section 5.3, 5.5.

Uses real DEMO_4 data throughout (registry, training data, ground truth),
not mocks -- this is the piece the mentor demo hinges on, so it needs to be
proven against the real pipeline, not a toy stand-in.
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
from loop.des_backend.demo4_ground_truth import ground_truth_fns_and_noise_for_demo4  # noqa: E402
from loop.des_backend.ground_truth_gp import DEFAULT_ARTIFACT_PATH  # noqa: E402
from loop.des_backend.manual_worklist import ManualWorklistDESBackend  # noqa: E402
from loop.des_backend.synthetic import SyntheticDESBackend  # noqa: E402
from loop.kpi_scope import DEMO_4  # noqa: E402
from loop.loop import (  # noqa: E402
    calibrate,
    compute_trust_scores,
    export_manual_round,
    fit_kpi_estimators,
    ingest_manual_round,
    propose_and_flag,
    run_loop,
)
from loop.novelty import NoveltyScorer  # noqa: E402
from loop.uq.dispatch import load_registry  # noqa: E402


def _real_data():
    X_df, Y_df = load_xy()
    return X_df, Y_df


def _far_ood_candidates(X_df, n=3):
    """Candidates far outside the training hull -- guaranteed to get
    flagged regardless of threshold, so tests don't depend on exactly
    which real KPI happens to be uncertain where."""
    base = X_df.iloc[0]
    rows = []
    for i in range(n):
        row = base.copy()
        row.iloc[0] = X_df.iloc[:, 0].max() * (5 + i)  # push first column far out
        rows.append(row)
    return pd.DataFrame(rows, index=[f"ood_{i}" for i in range(n)])


@unittest.skipUnless(DEFAULT_ARTIFACT_PATH.is_file(), "run fit_ground_truth.py first")
class FitAndScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.X_df, cls.Y_df = _real_data()
        cls.registry = load_registry()

    def test_fit_kpi_estimators_covers_all_demo4_paths(self):
        estimators = fit_kpi_estimators(DEMO_4, self.X_df, self.Y_df, self.registry)
        self.assertEqual(set(estimators), set(DEMO_4))
        for slug, est in estimators.items():
            result = est.predict_with_uncertainty(self.X_df.iloc[:3].to_numpy(dtype=float))
            self.assertEqual(result.mean.shape, (3,))

    def test_fit_kpi_estimators_drops_rows_with_nan_target_per_kpi(self):
        """Real bug (5-Sep): a manual round's real results file covered
        only some KPIs; the others got NaN for those new rows (T2.10's
        deliberate "persist every KPI present, don't discard rows" design,
        spec.md section 7 item 12). Retraining a KPI whose new rows are NaN
        used to crash (CatBoost refuses a NaN target) -- now those rows are
        dropped for THAT KPI's fit only, other KPIs unaffected."""
        X = self.X_df.copy()
        Y = self.Y_df.copy()
        extra_x = X.iloc[[0]].copy()
        extra_x.index = ["new_row"]
        X_ext = pd.concat([X, extra_x])
        extra_y = {col: [np.nan] for col in Y.columns}
        raw_key = self.registry["outputs"]["wt_ob_a_gb_ross"]["raw_key"]
        extra_y[raw_key] = [123.0]  # only one DEMO_4 KPI has a real value for this new row
        Y_ext = pd.concat([Y, pd.DataFrame(extra_y, index=["new_row"])])

        estimators = fit_kpi_estimators(DEMO_4, X_ext, Y_ext, self.registry)
        self.assertEqual(set(estimators), set(DEMO_4))
        for slug, est in estimators.items():
            result = est.predict_with_uncertainty(self.X_df.iloc[:2].to_numpy(dtype=float))
            self.assertEqual(result.mean.shape, (2,))
        # the 3 KPIs without a real value for "new_row" dropped exactly 1 row; the one with a value dropped 0
        for slug, est in estimators.items():
            expected_dropped = 0 if slug == "wt_ob_a_gb_ross" else 1
            self.assertEqual(est._n_rows_dropped_for_nan_target, expected_dropped, msg=slug)

    def test_compute_trust_scores_nonnegative_for_every_kpi(self):
        estimators = fit_kpi_estimators(DEMO_4, self.X_df, self.Y_df, self.registry)
        novelty = NoveltyScorer().fit(self.X_df.to_numpy(dtype=float))
        scales = {s: 1.0 for s in DEMO_4}
        scores = compute_trust_scores(DEMO_4, self.X_df.iloc[:5], estimators, novelty, scales)
        for idx, per_kpi in scores.items():
            self.assertEqual(set(per_kpi), set(DEMO_4))
            for v in per_kpi.values():
                self.assertGreaterEqual(v, 0.0)

    def test_calibrate_returns_one_threshold_per_kpi(self):
        estimators = fit_kpi_estimators(DEMO_4, self.X_df, self.Y_df, self.registry)
        novelty = NoveltyScorer().fit(self.X_df.to_numpy(dtype=float))
        scales = {s: 1.0 for s in DEMO_4}
        thresholds = calibrate(DEMO_4, self.X_df, estimators, novelty, scales, quantile=0.9)
        self.assertEqual(set(thresholds), set(DEMO_4))


@unittest.skipUnless(DEFAULT_ARTIFACT_PATH.is_file(), "run fit_ground_truth.py first")
class ProposeAndFlagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.X_df, cls.Y_df = _real_data()
        cls.registry = load_registry()
        cls.estimators = fit_kpi_estimators(DEMO_4, cls.X_df, cls.Y_df, cls.registry)
        cls.novelty = NoveltyScorer().fit(cls.X_df.to_numpy(dtype=float))
        cls.scales = {s: 1.0 for s in DEMO_4}

    def test_far_ood_candidates_get_flagged(self):
        thresholds = calibrate(DEMO_4, self.X_df, self.estimators, self.novelty, self.scales, quantile=0.5)
        ood = _far_ood_candidates(self.X_df)
        flagged, decisions = propose_and_flag(
            DEMO_4, ood, self.estimators, self.novelty, thresholds, self.scales
        )
        self.assertGreater(len(flagged), 0)
        for idx in flagged.index:
            self.assertTrue(decisions[idx].flagged)

    def test_max_batch_size_caps_flagged_set(self):
        thresholds = calibrate(DEMO_4, self.X_df, self.estimators, self.novelty, self.scales, quantile=0.01)
        flagged, _ = propose_and_flag(
            DEMO_4, self.X_df, self.estimators, self.novelty, thresholds, self.scales, max_batch_size=5
        )
        self.assertLessEqual(len(flagged), 5)

    def test_flagged_sorted_by_worst_score_first(self):
        thresholds = calibrate(DEMO_4, self.X_df, self.estimators, self.novelty, self.scales, quantile=0.01)
        flagged, decisions = propose_and_flag(
            DEMO_4, self.X_df, self.estimators, self.novelty, thresholds, self.scales
        )
        worst_scores = [max(decisions[idx].per_kpi_scores.values()) for idx in flagged.index]
        self.assertEqual(worst_scores, sorted(worst_scores, reverse=True))

    def test_empty_candidate_pool_raises(self):
        thresholds = calibrate(DEMO_4, self.X_df, self.estimators, self.novelty, self.scales, quantile=0.9)
        with self.assertRaises(ValueError):
            propose_and_flag(DEMO_4, pd.DataFrame(), self.estimators, self.novelty, thresholds, self.scales)


@unittest.skipUnless(DEFAULT_ARTIFACT_PATH.is_file(), "run fit_ground_truth.py first")
class RunLoopSyntheticEndToEndTests(unittest.TestCase):
    """The core DoD evidence (spec.md 5.5): flags a batch, simulates it,
    retrains, recalibrates, and the trust score moves sensibly afterward."""

    @classmethod
    def setUpClass(cls):
        cls.X_df, cls.Y_df = _real_data()
        fns, noise = ground_truth_fns_and_noise_for_demo4()
        cls.backend = SyntheticDESBackend(kpi_slugs=DEMO_4, ground_truth_fns=fns, noise_std=noise)

    def test_full_pass_grows_training_data_and_reports_scores(self):
        ood = _far_ood_candidates(self.X_df, n=2)
        result = run_loop(
            DEMO_4, ood, self.backend, self.X_df, self.Y_df,
            quantile=0.5, max_batch_size=5, n_replications=3, seed=1,
        )
        self.assertGreater(result["flagged_count"], 0)
        self.assertEqual(result["n_training_rows_after"], result["n_training_rows_before"] + result["flagged_count"])
        self.assertEqual(set(result["scores_before"]), set(result["flagged_ids"]))
        self.assertEqual(set(result["scores_after"]), set(result["flagged_ids"]))
        for slug in DEMO_4:
            self.assertIn(slug, result["estimators"])

    def test_nothing_flagged_returns_early_without_simulating(self):
        result = run_loop(
            DEMO_4, self.X_df.iloc[:3], self.backend, self.X_df, self.Y_df,
            quantile=0.999999, max_batch_size=5,
        )
        self.assertEqual(result["flagged_count"], 0)
        self.assertNotIn("estimators", result)

    def test_empty_kpi_slugs_raises(self):
        with self.assertRaises(ValueError):
            run_loop([], self.X_df.iloc[:2], self.backend, self.X_df, self.Y_df)


@unittest.skipUnless(DEFAULT_ARTIFACT_PATH.is_file(), "run fit_ground_truth.py first")
class ManualRoundRoundTripTests(unittest.TestCase):
    """export_manual_round() / ingest_manual_round() -- the two-phase path
    for ManualWorklistDESBackend (spec.md section 7 item 9). Uses a
    synthetic results file standing in for what a human would bring back
    from AnyLogic Cloud, so this is testable before any real manual run."""

    @classmethod
    def setUpClass(cls):
        cls.X_df, cls.Y_df = _real_data()
        cls.registry = load_registry()
        cls.backend = ManualWorklistDESBackend()

    def test_export_then_ingest_round_trip(self):
        ood = _far_ood_candidates(self.X_df, n=2)
        out_dir = ROOT / "tests" / "_scratch"
        out_stem = out_dir / "loop_manual_test"

        export_result = export_manual_round(
            DEMO_4, ood, self.backend, out_stem, self.X_df, self.Y_df,
            quantile=0.5, max_batch_size=5, n_replications=3, seed=7,
        )
        self.assertGreater(export_result["flagged_count"], 0)
        self.assertTrue(Path(export_result["worklist_path"]).is_file())
        self.assertTrue(Path(export_result["csv_path"]).is_file())
        csv_df = pd.read_csv(export_result["csv_path"])
        self.assertEqual(list(csv_df["n_replications"]), [3] * len(csv_df))
        self.assertEqual(list(csv_df["seed"]), [7] * len(csv_df))

        # stand-in for what a human would bring back from AnyLogic Cloud:
        flagged = export_result["flagged_batch"]
        rows = []
        for run_id in flagged.index:
            for rep in (1, 2):
                row = {"run_id": run_id, "replication": rep, "seed": rep}
                for slug in DEMO_4:
                    raw_key = self.registry["outputs"][slug]["raw_key"]
                    row[raw_key] = float(self.Y_df[raw_key].mean())
                rows.append(row)
        results_path = out_dir / "loop_manual_results.csv"
        pd.DataFrame(rows).to_csv(results_path, index=False)

        ingest_result = ingest_manual_round(
            DEMO_4, results_path, self.backend, flagged, self.X_df, self.Y_df, self.registry,
        )
        self.assertEqual(
            ingest_result["n_training_rows_after"],
            ingest_result["n_training_rows_before"] + len(flagged),
        )
        for slug in DEMO_4:
            self.assertIn(slug, ingest_result["estimators"])

        Path(export_result["worklist_path"]).unlink()
        Path(export_result["csv_path"]).unlink()
        results_path.unlink()
        out_dir.rmdir()

    def test_ingest_persists_kpi_columns_beyond_kpi_slugs(self):
        """A real AnyLogic run returns all 20 KPIs at once, regardless of
        which ones this round's loop was scoped to -- ingest_manual_round()
        should keep every KPI column the results file actually has, not
        just DEMO_4's 4 (spec.md section 7 item 12)."""
        ood = _far_ood_candidates(self.X_df, n=1)
        out_dir = ROOT / "tests" / "_scratch"
        out_stem = out_dir / "loop_manual_extra_kpi"
        export_result = export_manual_round(
            DEMO_4, ood, self.backend, out_stem, self.X_df, self.Y_df, quantile=0.5, max_batch_size=5,
        )
        flagged = export_result["flagged_batch"]

        extra_slug = "wt_ob_lb"  # a real registered KPI outside DEMO_4
        extra_raw_key = self.registry["outputs"][extra_slug]["raw_key"]
        rows = []
        for run_id in flagged.index:
            for rep in (1, 2):
                row = {"run_id": run_id, "replication": rep, "seed": rep}
                for slug in DEMO_4:
                    raw_key = self.registry["outputs"][slug]["raw_key"]
                    row[raw_key] = float(self.Y_df[raw_key].mean())
                row[extra_raw_key] = float(self.Y_df[extra_raw_key].mean())
                rows.append(row)
        results_path = out_dir / "loop_manual_extra_kpi_results.csv"
        pd.DataFrame(rows).to_csv(results_path, index=False)

        ingest_result = ingest_manual_round(
            DEMO_4, results_path, self.backend, flagged, self.X_df, self.Y_df, self.registry,
        )
        self.assertIn(extra_raw_key, ingest_result["Y_train"].columns)
        self.assertFalse(ingest_result["Y_train"].loc[flagged.index, extra_raw_key].isna().any())

        Path(export_result["worklist_path"]).unlink()
        Path(export_result["csv_path"]).unlink()
        results_path.unlink()
        out_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
