"""
Load NOLHC xlsx → X/Y parquet (nolhc_ml_engine_spec.md §4, §9).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from training_columns import (
    EXP_VALUES_FEATURE_COL_INDICES,
    OUTPUT_COLUMN_ORDER,
    TRAINING_COLUMN_ORDER,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_XLSX = PROJECT_ROOT / "data" / "raw" / "nolhc_runs.xlsx"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
EXPECTED_RUNS = 129


def _validate_no_nan(x: pd.DataFrame, y: pd.DataFrame) -> None:
    if x.isna().any().any():
        bad = x.columns[x.isna().any()].tolist()
        raise ValueError(f"NaN in X columns: {bad[:10]}")
    if y.isna().any().any():
        bad = y.columns[y.isna().any()].tolist()
        raise ValueError(f"NaN in Y columns: {bad[:10]}")


def load_from_xlsx(
    xlsx_path: Path,
    *,
    expect_rows: Optional[int] = EXPECTED_RUNS,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    """
    Read ExpValues + SimResults (header rows 1–3 skipped; data from row 4).
    Returns (X, Y, training_medians).
    """
    if not xlsx_path.is_file():
        raise FileNotFoundError(f"Missing source workbook: {xlsx_path}")

    exp = pd.read_excel(xlsx_path, sheet_name="ExpValues", header=None, skiprows=3, engine="openpyxl")
    sim = pd.read_excel(xlsx_path, sheet_name="SimResults", header=None, skiprows=3, engine="openpyxl")

    max_col = max(EXP_VALUES_FEATURE_COL_INDICES)
    if exp.shape[1] <= max_col:
        raise ValueError(
            f"ExpValues has only {exp.shape[1]} columns; need index up to {max_col}. "
            "Check sheet layout vs spec §5."
        )

    x = exp.iloc[:, EXP_VALUES_FEATURE_COL_INDICES].copy()
    x.columns = TRAINING_COLUMN_ORDER

    # SimResults: col 0 = run index; cols 1..20 = KPIs (20 outputs)
    if sim.shape[1] < 1 + len(OUTPUT_COLUMN_ORDER):
        raise ValueError(
            f"SimResults has {sim.shape[1]} columns; need at least {1 + len(OUTPUT_COLUMN_ORDER)}."
        )
    y = sim.iloc[:, 1 : 1 + len(OUTPUT_COLUMN_ORDER)].copy()
    y.columns = OUTPUT_COLUMN_ORDER

    for col in x.columns:
        x[col] = pd.to_numeric(x[col], errors="coerce")
    for col in y.columns:
        y[col] = pd.to_numeric(y[col], errors="coerce")

    _validate_no_nan(x, y)

    if len(x) != len(y):
        raise ValueError(f"Row count mismatch: ExpValues {len(x)} vs SimResults {len(y)}")

    if expect_rows is not None and len(x) != expect_rows:
        raise ValueError(f"Expected {expect_rows} runs, got {len(x)}")

    medians = {c: float(np.median(x[c].values)) for c in TRAINING_COLUMN_ORDER}

    return x, y, medians


def save_processed(
    x: pd.DataFrame,
    y: pd.DataFrame,
    medians: Dict[str, float],
    processed_dir: Optional[Path] = None,
) -> None:
    out = processed_dir or PROCESSED_DIR
    out.mkdir(parents=True, exist_ok=True)
    x.to_parquet(out / "X_train.parquet", index=False)
    y.to_parquet(out / "Y_train.parquet", index=False)
    with open(out / "training_medians.json", "w", encoding="utf-8") as f:
        json.dump(medians, f, indent=2)


def load_data(
    xlsx_path: Optional[Path] = None,
    *,
    expect_rows: Optional[int] = EXPECTED_RUNS,
    save: bool = True,
    processed_dir: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    path = xlsx_path or DEFAULT_XLSX
    x, y, medians = load_from_xlsx(path, expect_rows=expect_rows)
    if save:
        save_processed(x, y, medians, processed_dir)
    return x, y, medians


def load_parquet_pair(
    processed_dir: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    out = processed_dir or PROCESSED_DIR
    x = pd.read_parquet(out / "X_train.parquet")
    y = pd.read_parquet(out / "Y_train.parquet")
    return x, y


def append_runs_from_xlsx(
    xlsx_path: Path,
    *,
    processed_dir: Optional[Path] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    """Append rows from ``xlsx_path`` to existing parquet (concatenate; recompute medians)."""
    out = processed_dir or PROCESSED_DIR
    x_old, y_old = load_parquet_pair(out)
    x_new, y_new, _ = load_from_xlsx(xlsx_path, expect_rows=None)
    bx = pd.concat([x_old, x_new], ignore_index=True)
    by = pd.concat([y_old, y_new], ignore_index=True)
    if len(bx) != len(by):
        raise ValueError("Length mismatch after append")
    _validate_no_nan(bx, by)
    medians = {c: float(np.median(bx[c].values)) for c in TRAINING_COLUMN_ORDER}
    save_processed(bx, by, medians, out)
    return bx, by, medians
