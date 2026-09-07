"""
Load AnyLogic completed-runs workbook → feature/target DataFrames (spec §6).

Header row index 1; data from row 2. Sheet name ``Completed runs``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Union

import pandas as pd

from training_columns import (
    CONSTANT_COLS_TO_DROP,
    OUTPUT_COLUMN_ORDER,
    TRAINING_COLUMN_ORDER,
    validate_column_lists,
)

SHEET_NAME = "Completed runs"
HEADER_ROW = 1
# Canonical spec export has 228 successful runs; real files may differ (e.g. one Failed row → 227).
DEFAULT_EXPECTED_ROWS: Optional[int] = None

PathLike = Union[str, Path]


def _find_run_column(columns: pd.Index) -> str:
    cols = list(columns)
    for name in ("Run #", "Run#", "Run"):
        if name in cols:
            return name
    lower_map = {str(c).strip().lower(): c for c in cols}
    for key in ("run #", "run#", "run"):
        if key in lower_map:
            return str(lower_map[key])
    raise ValueError(f"No run id column found among columns: {cols[:20]}...")


def _strip_column_names(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    return out


def prepare_training_frames(
    df: pd.DataFrame,
    *,
    expect_rows: Optional[int] = DEFAULT_EXPECTED_ROWS,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Apply spec cleaning: drop null runs, non-successful rows, constant columns;
    replace ``<Data>`` sentinels; numeric coerce; fill NaN with 0.

    Returns X (153 cols) and Y (136 cols) aligned to ``TRAINING_COLUMN_ORDER`` /
    ``OUTPUT_COLUMN_ORDER``.
    """
    validate_column_lists()
    df = _strip_column_names(df)
    run_col = _find_run_column(df.columns)
    if "Status" not in df.columns:
        raise ValueError("Expected a 'Status' column in the completed runs sheet.")

    df = df.dropna(subset=[run_col])
    status = df["Status"].astype(str).str.strip().str.lower()
    df = df.loc[status == "successful"].copy()

    for c in CONSTANT_COLS_TO_DROP:
        if c in df.columns:
            df = df.drop(columns=[c])

    df = df.replace("<Data>", float("nan"))
    df = df.replace(r"^\s*<Data>\s*$", float("nan"), regex=True)

    for col in TRAINING_COLUMN_ORDER + OUTPUT_COLUMN_ORDER:
        if col not in df.columns:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df[col] = df[col].fillna(0.0)

    missing_in = [c for c in TRAINING_COLUMN_ORDER if c not in df.columns]
    if missing_in:
        raise ValueError(
            "Missing input column(s) after cleaning: "
            f"{missing_in[:5]}{'...' if len(missing_in) > 5 else ''}"
        )
    missing_out = [c for c in OUTPUT_COLUMN_ORDER if c not in df.columns]
    if missing_out:
        raise ValueError(
            "Missing output column(s): "
            f"{missing_out[:5]}{'...' if len(missing_out) > 5 else ''}"
        )

    x_df = df[TRAINING_COLUMN_ORDER].astype("float64").copy()
    y_df = df[OUTPUT_COLUMN_ORDER].astype("float64").copy()

    if expect_rows is not None and len(x_df) != expect_rows:
        raise ValueError(
            f"Expected {expect_rows} successful rows, got {len(x_df)}. "
            "Pass expect_rows=None to skip this check."
        )

    return x_df, y_df


def load_xlsx(
    path: PathLike,
    *,
    expect_rows: Optional[int] = DEFAULT_EXPECTED_ROWS,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Read ``Completed runs`` sheet and return ``(X, Y)``."""
    path = Path(path)
    raw = pd.read_excel(path, sheet_name=SHEET_NAME, header=HEADER_ROW, engine="openpyxl")
    return prepare_training_frames(raw, expect_rows=expect_rows)


def save_processed_parquet(
    x_df: pd.DataFrame,
    y_df: pd.DataFrame,
    processed_dir: PathLike,
) -> Tuple[Path, Path]:
    """Write ``X_train.parquet`` and ``Y_train.parquet`` under ``processed_dir``."""
    processed_dir = Path(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    xp = processed_dir / "X_train.parquet"
    yp = processed_dir / "Y_train.parquet"
    x_df.to_parquet(xp, index=False)
    y_df.to_parquet(yp, index=False)
    return xp, yp
