"""Tests for training column lists and data_loader (Task 3)."""

from pathlib import Path

import pandas as pd
import pytest

from data_loader import (
    prepare_training_frames,
    save_processed_parquet,
)
from training_columns import (
    CONSTANT_COLS_TO_DROP,
    OUTPUT_COLUMN_ORDER,
    TRAINING_COLUMN_ORDER,
    validate_column_lists,
)


def test_training_column_lists():
    validate_column_lists()
    assert len(TRAINING_COLUMN_ORDER) == 153
    assert len(OUTPUT_COLUMN_ORDER) == 136
    assert len(CONSTANT_COLS_TO_DROP) == 5
    assert not set(TRAINING_COLUMN_ORDER) & set(OUTPUT_COLUMN_ORDER)


def test_prepare_training_frames_minimal():
    """Two synthetic successful rows with full input/output column sets."""
    meta = {"Run #": [1.0, 2.0], "Status": ["Successful", "Successful"]}
    inputs = {c: [0.0, 1.0] for c in TRAINING_COLUMN_ORDER}
    outputs = {c: [0.0, 2.0] for c in OUTPUT_COLUMN_ORDER}
    df = pd.DataFrame({**meta, **inputs, **outputs})
    x_df, y_df = prepare_training_frames(df, expect_rows=None)
    assert x_df.shape == (2, 153)
    assert y_df.shape == (2, 136)
    assert list(x_df.columns) == TRAINING_COLUMN_ORDER
    assert list(y_df.columns) == OUTPUT_COLUMN_ORDER


def test_drops_constant_columns():
    """Constant input columns are removed before selecting TRAINING_COLUMN_ORDER."""
    meta = {"Run #": [1.0], "Status": ["Successful"]}
    inputs = {c: [0.0] for c in TRAINING_COLUMN_ORDER}
    for c in CONSTANT_COLS_TO_DROP:
        inputs[c] = [0.0]
    outputs = {c: [0.0] for c in OUTPUT_COLUMN_ORDER}
    df = pd.DataFrame({**meta, **inputs, **outputs})
    x_df, y_df = prepare_training_frames(df, expect_rows=None)
    assert x_df.shape == (1, 153)
    assert y_df.shape == (1, 136)


def test_data_sentinel_replaced():
    meta = {"Run #": [1.0], "Status": ["Successful"]}
    inputs = {c: [0.0] for c in TRAINING_COLUMN_ORDER}
    outputs = {c: [0.0] for c in OUTPUT_COLUMN_ORDER}
    inputs[TRAINING_COLUMN_ORDER[0]] = ["<Data>"]
    df = pd.DataFrame({**meta, **inputs, **outputs})
    x_df, _ = prepare_training_frames(df, expect_rows=None)
    assert float(x_df.iloc[0, 0]) == 0.0


@pytest.mark.integration
def test_load_real_xlsx_when_present():
    """Requires an AnyLogic export under ``data/raw/`` (see README)."""
    root = Path(__file__).resolve().parents[1]
    raw_dir = root / "data" / "raw"
    candidates = [
        raw_dir / "completed_runs.xlsx",
        raw_dir / "Post-Brexit Sector Based Model - PostBrexit_latest model - Completed runs.xlsx",
    ]
    xlsx = next((p for p in candidates if p.is_file()), None)
    if xlsx is None:
        pytest.skip(f"Place source workbook in {raw_dir}")

    from data_loader import load_xlsx

    x_df, y_df = load_xlsx(xlsx)
    assert x_df.shape[1] == 153 and y_df.shape[1] == 136
    assert x_df.shape[0] == y_df.shape[0] >= 200


def test_save_processed_parquet_roundtrip(tmp_path):
    meta = {"Run #": [1.0], "Status": ["Successful"]}
    inputs = {c: [3.14] for c in TRAINING_COLUMN_ORDER}
    outputs = {c: [2.0] for c in OUTPUT_COLUMN_ORDER}
    df = pd.DataFrame({**meta, **inputs, **outputs})
    x_df, y_df = prepare_training_frames(df, expect_rows=None)
    xp, yp = save_processed_parquet(x_df, y_df, tmp_path)
    assert xp.is_file() and yp.is_file()
    xr = pd.read_parquet(xp)
    assert abs(float(xr.iloc[0, 0]) - 3.14) < 1e-9
