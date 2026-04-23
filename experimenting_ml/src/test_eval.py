"""
Step 7: test-set metrics from saved scaler + joblib models (spec §7).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from models import NEEDS_SCALING, get_models


def _safe_filename(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", s)


def load_split_meta(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def list_trained_model_names(trained_dir: Path) -> List[str]:
    """
    Infer model names from the first target subdirectory (stems of *.joblib).
    Matches how ``save_trained_bundle`` names files (``_safe_filename(model)``).
    """
    subs = sorted(
        [d for d in trained_dir.iterdir() if d.is_dir()],
        key=lambda p: p.name,
    )
    if not subs:
        return []
    return sorted([p.stem for p in subs[0].glob("*.joblib")])


def compute_test_results(
    X: pd.DataFrame,
    Y: pd.DataFrame,
    test_idx: List[int],
    trained_dir: Path,
    *,
    model_names: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Load fitted estimators from trained_dir; predict on X_test; return nested dict
    with rmse, mae, r2, y_pred, residuals (numpy arrays in memory).
    """
    mnames = model_names or list(get_models().keys())
    scaler = joblib.load(trained_dir / "scaler.joblib")

    X_test = X.iloc[test_idx].reset_index(drop=True)
    Y_test = Y.iloc[test_idx].reset_index(drop=True)
    X_raw = X_test.to_numpy(dtype=float)
    X_scaled = scaler.transform(X_raw)

    out: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for target in Y_test.columns:
        out[target] = {}
        y_true = Y_test[target].to_numpy(dtype=float)
        tdir = trained_dir / _safe_filename(target)

        for mname in mnames:
            est = joblib.load(tdir / f"{_safe_filename(mname)}.joblib")
            if mname in NEEDS_SCALING:
                y_pred = est.predict(X_scaled)
            else:
                y_pred = est.predict(X_raw)

            y_pred = np.asarray(y_pred, dtype=float)
            residuals = y_true - y_pred
            rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
            mae = float(mean_absolute_error(y_true, y_pred))
            r2 = float(r2_score(y_true, y_pred))

            out[target][mname] = {
                "rmse": rmse,
                "mae": mae,
                "r2": r2,
                "y_pred": y_pred,
                "residuals": residuals,
            }

    return out


def test_results_to_jsonable(
    test_results: Dict[str, Dict[str, Dict[str, Any]]],
) -> Dict[str, Any]:
    """Strip numpy arrays to lists for JSON."""
    serial: Dict[str, Any] = {}
    for t, per_m in test_results.items():
        serial[t] = {}
        for m, r in per_m.items():
            serial[t][m] = {
                "rmse": r["rmse"],
                "mae": r["mae"],
                "r2": r["r2"],
                "y_pred": np.asarray(r["y_pred"]).tolist(),
                "residuals": np.asarray(r["residuals"]).tolist(),
            }
    return serial
