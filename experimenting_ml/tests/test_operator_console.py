"""
Operator-console backend (technical report §13): pending queue + the thin
operator_api wrappers. The heavy loop logic is covered by the existing loop
tests; this checks the queue semantics and that the wrappers return the
shapes the UI expects without mutating committed data.
"""

from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


class PendingQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        from loop import pending_queue

        self.pq = pending_queue
        self._tmp = tempfile.TemporaryDirectory()
        self.pq.QUEUE_DIR = Path(self._tmp.name)
        self.pq.QUEUE_PATH = self.pq.QUEUE_DIR / "pending_queue.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_add_then_list(self) -> None:
        e = self.pq.add({"NA_Im": 1.0, "A_Im": 2.0}, reason="wide interval")
        self.assertIsNotNone(e)
        entries = self.pq.list_entries("open")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["reason"], "wide interval")
        self.assertEqual(entries[0]["status"], "open")

    def test_near_duplicate_is_merged_not_appended(self) -> None:
        self.pq.add({"NA_Im": 100.0}, reason="r")
        merged = self.pq.add({"NA_Im": 100.00001}, reason="r")
        self.assertIsNone(merged)  # de-duped
        entries = self.pq.list_entries("open")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["seen_count"], 2)

    def test_dismiss_removes_from_open(self) -> None:
        e = self.pq.add({"NA_Im": 1.0}, reason="r")
        self.assertTrue(self.pq.set_status(e["id"], "dismissed"))
        self.assertEqual(self.pq.list_entries("open"), [])

    def test_missing_file_is_empty_not_error(self) -> None:
        self.assertEqual(self.pq.list_entries("open"), [])


class OperatorApiShapeTests(unittest.TestCase):
    """Read-only calls only — nothing here writes to the committed dataset."""

    def test_dataset_status_shape(self) -> None:
        from loop import operator_api

        d = operator_api.dataset_status()
        self.assertIn("n_training_rows", d)
        self.assertIn("per_kpi_rows", d)
        self.assertIn("rounds", d)
        self.assertGreaterEqual(d["n_training_rows"], 129)
        self.assertIsInstance(d["rounds"], list)

    def test_pending_list_shape(self) -> None:
        from loop import operator_api

        d = operator_api.pending_list()
        self.assertIn("entries", d)
        self.assertIsInstance(d["entries"], list)

    def test_ingest_unknown_round_is_clean_error(self) -> None:
        from loop import operator_api

        d = operator_api.ingest_round("round_does_not_exist", results_csv_text="run_id,replication,seed\n")
        self.assertFalse(d["ok"])
        self.assertIn("No round", d["error"])

    def test_ingest_no_results_at_all_is_clean_error(self) -> None:
        """6-Sep: neither pasted text nor an uploaded file -- must not
        crash trying to guess, just say so."""
        from loop import operator_api

        d = operator_api.ingest_round("round_does_not_exist")
        self.assertFalse(d["ok"])
        self.assertIn("No results provided", d["error"])


class IngestRoundFileFormatTests(unittest.TestCase):
    """6-Sep finding: the operator console's file picker only accepted
    .csv, and even a relaxed picker would have corrupted a real .xlsx
    upload -- file.text() on a binary file, then written with write_text().
    A real AnyLogic Cloud export is normally .xlsx, not .csv. These test
    the actual fix: results_content_b64 (+ filename) as the real-file path,
    base64-decoded and written back out with write_bytes() under the
    right extension, same as ManualWorklistDESBackend.ingest_results()
    already handles for the CLI."""

    @classmethod
    def setUpClass(cls):
        from loop.des_backend.ground_truth_gp import DEFAULT_ARTIFACT_PATH

        if not DEFAULT_ARTIFACT_PATH.is_file():
            raise unittest.SkipTest("run fit_ground_truth.py first")

    def setUp(self):
        import shutil

        from loop import cli_export_manual_round, dataset_store
        from loop.uq.dispatch import load_registry

        self.dataset_store = dataset_store
        self._orig_dir = dataset_store.MANUAL_ROUNDS_DIR
        self._orig_manifest = dataset_store.MANIFEST_PATH
        self._orig_x = dataset_store.EXTENDED_X_PATH
        self._orig_y = dataset_store.EXTENDED_Y_PATH

        self.tmp_dir = Path(__file__).resolve().parent / "_scratch_operator_ingest"
        dataset_store.MANUAL_ROUNDS_DIR = self.tmp_dir
        dataset_store.MANIFEST_PATH = self.tmp_dir / "rounds_manifest.json"
        dataset_store.EXTENDED_X_PATH = self.tmp_dir / "extended_X_train.parquet"
        dataset_store.EXTENDED_Y_PATH = self.tmp_dir / "extended_Y_train.parquet"

        self.registry = load_registry()
        cli_export_manual_round.main([
            "--kpi-scope", "demo4", "--n-candidates", "12", "--quantile", "0.3",
            "--max-batch-size", "4", "--n-replications", "1", "--seed", "7",
            "--out-dir", str(self.tmp_dir),
        ])
        entry = dataset_store.load_manifest()[0]
        self.round_id = entry["round_id"]
        self.entry = entry
        self._shutil = shutil

    def tearDown(self):
        if self.tmp_dir.exists():
            self._shutil.rmtree(self.tmp_dir)
        self.dataset_store.MANUAL_ROUNDS_DIR = self._orig_dir
        self.dataset_store.MANIFEST_PATH = self._orig_manifest
        self.dataset_store.EXTENDED_X_PATH = self._orig_x
        self.dataset_store.EXTENDED_Y_PATH = self._orig_y

    def _fake_results_df(self):
        import pandas as pd

        requests_df = pd.read_csv(self.entry["run_requests_csv"])
        rows = []
        for run_id in requests_df["run_id"]:
            row = {"run_id": run_id, "replication": 1, "seed": 1}
            for slug in self.entry["kpi_slugs"]:
                raw_key = self.registry["outputs"][slug]["raw_key"]
                row[raw_key] = 42.0
            rows.append(row)
        return pd.DataFrame(rows), len(requests_df)

    def test_pasted_csv_text_still_works(self) -> None:
        from loop import operator_api

        df, n = self._fake_results_df()
        d = operator_api.ingest_round(self.round_id, results_csv_text=df.to_csv(index=False))
        self.assertTrue(d.get("ok"), d)
        self.assertEqual(d["rows_added"], n)

    def test_base64_csv_upload_works(self) -> None:
        """Same content as the pasted-text case, sent the "real file
        upload" way -- proves the base64 path isn't CSV-specific plumbing
        that happens to also handle text."""
        import base64

        from loop import operator_api

        df, n = self._fake_results_df()
        content = base64.b64encode(df.to_csv(index=False).encode("utf-8")).decode("ascii")
        d = operator_api.ingest_round(
            self.round_id, results_content_b64=content, filename="anylogic_results.csv"
        )
        self.assertTrue(d.get("ok"), d)
        self.assertEqual(d["rows_added"], n)

    def test_base64_xlsx_upload_works(self) -> None:
        """The actual real-world case this was built for: a real AnyLogic
        Cloud export is an .xlsx, not a .csv."""
        import base64
        import io

        from loop import operator_api

        df, n = self._fake_results_df()
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        content = base64.b64encode(buf.getvalue()).decode("ascii")
        d = operator_api.ingest_round(
            self.round_id, results_content_b64=content, filename="Completed runs.xlsx"
        )
        self.assertTrue(d.get("ok"), d)
        self.assertEqual(d["rows_added"], n)

    def test_mislabeled_xlsx_named_csv_still_ingests_correctly(self) -> None:
        """6-Sep finding #2, reported directly by a real user upload: a
        real AnyLogic Cloud export's actual bytes were a genuine .xlsx
        (ZIP-based), but the file was named "candidate_run_outputs.csv".
        Trusting the filename's extension alone would hand binary ZIP
        bytes to pandas.read_csv. Content must be sniffed, not just the
        name -- this proves the exact case that broke first."""
        import base64
        import io

        from loop import operator_api

        df, n = self._fake_results_df()
        buf = io.BytesIO()
        df.to_excel(buf, index=False)  # genuine .xlsx bytes ...
        content = base64.b64encode(buf.getvalue()).decode("ascii")
        d = operator_api.ingest_round(
            self.round_id, results_content_b64=content, filename="candidate_run_outputs.csv"  # ... lying name
        )
        self.assertTrue(d.get("ok"), d)
        self.assertEqual(d["rows_added"], n)

    def test_bad_base64_is_clean_error_not_crash(self) -> None:
        from loop import operator_api

        d = operator_api.ingest_round(
            self.round_id, results_content_b64="not valid base64 !!!", filename="x.xlsx"
        )
        self.assertFalse(d["ok"])
        self.assertIn("could not be decoded", d["error"])


if __name__ == "__main__":
    unittest.main()
