"""
Integration tests for the two CLI entrypoints (T2.11, spec.md section 7
item 12): cli_export_manual_round.py / cli_ingest_manual_round.py, run as
real argparse invocations (main(argv)) against a temp dataset_store
directory -- this is the actual reproducible trigger the mentor/future
work will use, so it's tested as a whole, not just its pieces.
"""

from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd  # noqa: E402

from loop import cli_export_manual_round, cli_ingest_manual_round, dataset_store  # noqa: E402
from loop.des_backend.ground_truth_gp import DEFAULT_ARTIFACT_PATH  # noqa: E402
from loop.uq.dispatch import load_registry  # noqa: E402


@unittest.skipUnless(DEFAULT_ARTIFACT_PATH.is_file(), "run fit_ground_truth.py first")
class CliManualRoundTests(unittest.TestCase):
    def setUp(self):
        self._orig_dir = dataset_store.MANUAL_ROUNDS_DIR
        self._orig_manifest = dataset_store.MANIFEST_PATH
        self._orig_x = dataset_store.EXTENDED_X_PATH
        self._orig_y = dataset_store.EXTENDED_Y_PATH

        self.tmp_dir = ROOT / "tests" / "_scratch_cli"
        dataset_store.MANUAL_ROUNDS_DIR = self.tmp_dir
        dataset_store.MANIFEST_PATH = self.tmp_dir / "rounds_manifest.json"
        dataset_store.EXTENDED_X_PATH = self.tmp_dir / "extended_X_train.parquet"
        dataset_store.EXTENDED_Y_PATH = self.tmp_dir / "extended_Y_train.parquet"

        self.registry = load_registry()

    def tearDown(self):
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)
        dataset_store.MANUAL_ROUNDS_DIR = self._orig_dir
        dataset_store.MANIFEST_PATH = self._orig_manifest
        dataset_store.EXTENDED_X_PATH = self._orig_x
        dataset_store.EXTENDED_Y_PATH = self._orig_y

    def test_export_then_ingest_round_trip_via_cli(self):
        cli_export_manual_round.main([
            "--kpi-scope", "demo4",
            "--n-candidates", "15",
            "--quantile", "0.3",
            "--max-batch-size", "5",
            "--n-replications", "3",
            "--seed", "123",
            "--out-dir", str(self.tmp_dir),
        ])

        manifest = dataset_store.load_manifest()
        self.assertEqual(len(manifest), 1)
        entry = manifest[0]
        self.assertEqual(entry["status"], "exported_pending_manual_run")
        round_id = entry["round_id"]
        self.assertTrue(Path(entry["run_requests_csv"]).is_file())
        self.assertTrue(Path(entry["worklist_xlsx"]).is_file())

        # stand-in for the human's AnyLogic Cloud export
        requests_df = pd.read_csv(entry["run_requests_csv"])
        rows = []
        for run_id in requests_df["run_id"]:
            for rep in (1, 2, 3):
                row = {"run_id": run_id, "replication": rep, "seed": rep}
                for slug in entry["kpi_slugs"]:
                    raw_key = self.registry["outputs"][slug]["raw_key"]
                    row[raw_key] = 42.0
                rows.append(row)
        results_path = self.tmp_dir / "fake_anylogic_results.csv"
        pd.DataFrame(rows).to_csv(results_path, index=False)

        cli_ingest_manual_round.main([
            "--round-id", round_id,
            "--results", str(results_path),
        ])

        manifest = dataset_store.load_manifest()
        self.assertEqual(manifest[0]["status"], "ingested")
        self.assertEqual(manifest[0]["n_rows_added"], len(requests_df))

        X, Y = dataset_store.load_current_training_data()
        self.assertEqual(len(X), 129 + len(requests_df))
        self.assertTrue(set(requests_df["run_id"]).issubset(set(X.index)))

    def test_ingest_refuses_to_double_ingest_same_round(self):
        cli_export_manual_round.main([
            "--n-candidates", "15", "--quantile", "0.3", "--max-batch-size", "3",
            "--seed", "1", "--out-dir", str(self.tmp_dir),
        ])
        entry = dataset_store.load_manifest()[0]
        round_id = entry["round_id"]

        requests_df = pd.read_csv(entry["run_requests_csv"])
        rows = []
        for run_id in requests_df["run_id"]:
            row = {"run_id": run_id, "replication": 1, "seed": 1}
            for slug in entry["kpi_slugs"]:
                raw_key = self.registry["outputs"][slug]["raw_key"]
                row[raw_key] = 1.0
            rows.append(row)
        results_path = self.tmp_dir / "results.csv"
        pd.DataFrame(rows).to_csv(results_path, index=False)

        cli_ingest_manual_round.main(["--round-id", round_id, "--results", str(results_path)])
        with self.assertRaises(SystemExit):
            cli_ingest_manual_round.main(["--round-id", round_id, "--results", str(results_path)])

    def test_ingest_unknown_round_id_raises(self):
        with self.assertRaises(SystemExit):
            cli_ingest_manual_round.main(["--round-id", "not_a_real_round", "--results", "/tmp/x.csv"])

    def test_proven6_round_trip_via_cli(self):
        """spec.md section 7 item 13: --kpi-scope proven6 uses PROVEN_6's
        benchmarked winning methods, not the generic dispatch, and
        cli_ingest_manual_round.py must auto-select the matching mechanism
        from the manifest (no --kpi-scope flag exists on ingest anymore)."""
        cli_export_manual_round.main([
            "--kpi-scope", "proven6",
            "--n-candidates", "15",
            "--quantile", "0.3",
            "--max-batch-size", "5",
            "--n-replications", "3",
            "--seed", "123",
            "--out-dir", str(self.tmp_dir),
        ])

        manifest = dataset_store.load_manifest()
        self.assertEqual(len(manifest), 1)
        entry = manifest[0]
        self.assertEqual(entry["kpi_scope"], "proven6")
        self.assertEqual(set(entry["kpi_slugs"]), {
            "wt_ob_lb", "tt_ob_lb", "uti_cus_r", "wt_ob_a_gb_dub", "wt_ib_na_ross", "tt_ib_lb",
        })
        round_id = entry["round_id"]

        requests_df = pd.read_csv(entry["run_requests_csv"])
        rows = []
        for run_id in requests_df["run_id"]:
            for rep in (1, 2):
                row = {"run_id": run_id, "replication": rep, "seed": rep}
                for slug in entry["kpi_slugs"]:
                    raw_key = self.registry["outputs"][slug]["raw_key"]
                    row[raw_key] = 1.0
                rows.append(row)
        results_path = self.tmp_dir / "proven6_results.csv"
        pd.DataFrame(rows).to_csv(results_path, index=False)

        cli_ingest_manual_round.main(["--round-id", round_id, "--results", str(results_path)])

        manifest = dataset_store.load_manifest()
        self.assertEqual(manifest[0]["status"], "ingested")
        X, _ = dataset_store.load_current_training_data()
        self.assertEqual(len(X), 129 + len(requests_df))

    def test_export_nothing_flagged_when_candidates_are_in_sample(self):
        """Uses real training rows as the candidate pool -- these should
        score at/under their own calibration quantile almost by
        definition, unlike --n-candidates' random-in-bounds samples, which
        (correctly -- this is real design sparsity being detected, not a
        bug) tend to land in low-density gaps and get flagged even at a
        near-1.0 quantile."""
        import sys as _sys
        from pathlib import Path as _Path
        _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "src"))
        from data import load_xy

        X_df, _ = load_xy()
        in_sample_csv = self.tmp_dir / "in_sample_candidates.csv"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        X_df.iloc[:5].to_csv(in_sample_csv)

        cli_export_manual_round.main([
            "--candidates-csv", str(in_sample_csv), "--quantile", "0.999999",
            "--out-dir", str(self.tmp_dir),
        ])
        # nothing flagged -> no manifest entry written, no crash
        self.assertEqual(dataset_store.load_manifest(), [])


if __name__ == "__main__":
    unittest.main()
