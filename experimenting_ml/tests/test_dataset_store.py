"""
Tests for dataset_store.py (T2.10, spec.md section 7 item 12) -- the
persistent, append-only home for the growing training set + round manifest.

Uses a real temp directory swapped in for MANUAL_ROUNDS_DIR so these tests
never touch the real experimenting_ml/data/manual_rounds/ directory or the
real, pristine 129-row parquet files.
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

from loop import dataset_store  # noqa: E402


class DatasetStoreTests(unittest.TestCase):
    def setUp(self):
        self._orig_dir = dataset_store.MANUAL_ROUNDS_DIR
        self._orig_manifest = dataset_store.MANIFEST_PATH
        self._orig_x = dataset_store.EXTENDED_X_PATH
        self._orig_y = dataset_store.EXTENDED_Y_PATH

        self.tmp_dir = ROOT / "tests" / "_scratch_dataset_store"
        dataset_store.MANUAL_ROUNDS_DIR = self.tmp_dir
        dataset_store.MANIFEST_PATH = self.tmp_dir / "rounds_manifest.json"
        dataset_store.EXTENDED_X_PATH = self.tmp_dir / "extended_X_train.parquet"
        dataset_store.EXTENDED_Y_PATH = self.tmp_dir / "extended_Y_train.parquet"

    def tearDown(self):
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)
        dataset_store.MANUAL_ROUNDS_DIR = self._orig_dir
        dataset_store.MANIFEST_PATH = self._orig_manifest
        dataset_store.EXTENDED_X_PATH = self._orig_x
        dataset_store.EXTENDED_Y_PATH = self._orig_y

    def test_new_round_id_is_unique_and_sortable(self):
        a = dataset_store.new_round_id()
        b = dataset_store.new_round_id()
        self.assertTrue(a.startswith("round_"))
        self.assertLessEqual(a, b)  # timestamp-based, non-decreasing

    def test_load_current_training_data_falls_back_to_original_129_when_no_extension(self):
        X, Y = dataset_store.load_current_training_data()
        self.assertEqual(len(X), 129)
        self.assertEqual(len(Y), 129)

    def test_append_round_then_load_returns_original_plus_new(self):
        X_new = pd.DataFrame({"NA_Im": [1.0, 2.0]}, index=["r1", "r2"])
        Y_new = pd.DataFrame({"TT_OB_Agri": [10.0, 20.0]}, index=["r1", "r2"])
        dataset_store.append_round(X_new, Y_new)

        X, Y = dataset_store.load_current_training_data()
        self.assertEqual(len(X), 131)
        self.assertIn("r1", X.index)
        self.assertIn("r2", Y.index)

    def test_second_round_accumulates_on_top_of_first(self):
        dataset_store.append_round(
            pd.DataFrame({"NA_Im": [1.0]}, index=["r1"]),
            pd.DataFrame({"TT_OB_Agri": [10.0]}, index=["r1"]),
        )
        dataset_store.append_round(
            pd.DataFrame({"NA_Im": [2.0]}, index=["r2"]),
            pd.DataFrame({"TT_OB_Agri": [20.0]}, index=["r2"]),
        )
        X, _ = dataset_store.load_current_training_data()
        self.assertEqual(len(X), 131)
        self.assertEqual(set(X.index[-2:]), {"r1", "r2"})

    def test_append_round_rejects_index_collision(self):
        dataset_store.append_round(
            pd.DataFrame({"NA_Im": [1.0]}, index=["dup"]),
            pd.DataFrame({"TT_OB_Agri": [10.0]}, index=["dup"]),
        )
        with self.assertRaises(ValueError):
            dataset_store.append_round(
                pd.DataFrame({"NA_Im": [2.0]}, index=["dup"]),
                pd.DataFrame({"TT_OB_Agri": [20.0]}, index=["dup"]),
            )

    def test_append_round_rejects_collision_with_original_129(self):
        with self.assertRaises(ValueError):
            dataset_store.append_round(
                pd.DataFrame({"NA_Im": [1.0]}, index=[0]),  # collides with the original's integer index
                pd.DataFrame({"TT_OB_Agri": [10.0]}, index=[0]),
            )

    def test_append_round_empty_raises(self):
        with self.assertRaises(ValueError):
            dataset_store.append_round(pd.DataFrame(), pd.DataFrame())

    def test_append_round_mismatched_index_raises(self):
        with self.assertRaises(ValueError):
            dataset_store.append_round(
                pd.DataFrame({"NA_Im": [1.0]}, index=["r1"]),
                pd.DataFrame({"TT_OB_Agri": [10.0]}, index=["different_id"]),
            )

    def test_manifest_round_trip(self):
        round_id = dataset_store.new_round_id()
        dataset_store.record_round_exported(
            round_id, ["tt_ob_agri"], ["r1", "r2"], {"tt_ob_agri": 0.5}, 5, 42,
            Path("/x/requests.csv"), Path("/x/worklist.xlsx"),
        )
        manifest = dataset_store.load_manifest()
        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0]["status"], "exported_pending_manual_run")

        dataset_store.record_round_ingested(round_id, Path("/x/results.csv"), n_rows_added=2, n_training_rows_after=131)
        manifest = dataset_store.load_manifest()
        self.assertEqual(manifest[0]["status"], "ingested")
        self.assertEqual(manifest[0]["n_rows_added"], 2)

    def test_record_round_ingested_unknown_round_raises(self):
        with self.assertRaises(KeyError):
            dataset_store.record_round_ingested("nonexistent_round", Path("/x/results.csv"), 1, 130)


if __name__ == "__main__":
    unittest.main()
