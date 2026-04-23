"""Data loader tests (spec §16); require workbook at data/raw/nolhc_runs.xlsx."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_loader import DEFAULT_XLSX, load_from_xlsx  # noqa: E402
from training_columns import TRAINING_COLUMN_ORDER  # noqa: E402

XLSX = DEFAULT_XLSX


@pytest.mark.skipif(not XLSX.is_file(), reason=f"Missing {XLSX} (copy NOLHC xlsx per spec §3)")
def test_load_xlsx_shapes_and_no_nan() -> None:
    x, y, _medians = load_from_xlsx(XLSX, expect_rows=129)
    assert x.shape[0] == 129
    assert y.shape[0] == 129
    assert x.shape[1] == len(TRAINING_COLUMN_ORDER)
    assert y.shape[1] == 20
    assert not x.isna().any().any()
    assert not y.isna().any().any()
    assert list(x.columns) == TRAINING_COLUMN_ORDER
