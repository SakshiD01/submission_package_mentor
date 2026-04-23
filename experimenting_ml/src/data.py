"""
Load NOLHC X/Y — parquet (preferred) or xlsx via nolhc_ml data_loader.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Tuple

import pandas as pd

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EXPERIMENT_ROOT.parent
NOLHC_SRC = REPO_ROOT / "nolhc_ml" / "src"
DEFAULT_PARQUET_DIR = REPO_ROOT / "nolhc_ml" / "data" / "processed"
DEFAULT_XLSX = REPO_ROOT / "nolhc_ml" / "data" / "raw" / "nolhc_runs.xlsx"


def load_xy(
    *,
    parquet_dir: Path | None = None,
    xlsx_path: Path | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if xlsx_path is not None:
        if str(NOLHC_SRC) not in sys.path:
            sys.path.insert(0, str(NOLHC_SRC))
        from data_loader import load_from_xlsx  # noqa: WPS433

        x, y, _ = load_from_xlsx(Path(xlsx_path), expect_rows=129)
        return x, y

    pdir = Path(parquet_dir) if parquet_dir is not None else DEFAULT_PARQUET_DIR
    xf = pdir / "X_train.parquet"
    yf = pdir / "Y_train.parquet"
    if xf.is_file() and yf.is_file():
        return pd.read_parquet(xf), pd.read_parquet(yf)

    if DEFAULT_XLSX.is_file():
        return load_xy(xlsx_path=DEFAULT_XLSX)

    raise FileNotFoundError(
        f"No data: put parquet in {pdir} or xlsx at {DEFAULT_XLSX}, "
        "or pass --xlsx explicitly."
    )
