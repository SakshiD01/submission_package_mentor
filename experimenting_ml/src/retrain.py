"""
Step 6: refit each model on full training set with CV best_params (spec §6).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.preprocessing import StandardScaler

from models import NEEDS_SCALING, get_models


def _coerce_params(model_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Fix JSON round-trip issues (e.g. MLP hidden_layer_sizes as list)."""
    out = {}
    for k, v in params.items():
        if k == "hidden_layer_sizes" and model_name == "MLP" and isinstance(v, list):
            out[k] = tuple(v)
        else:
            out[k] = v
    return out


def _safe_filename(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", s)


def fit_full_training_models(
    X_train: pd.DataFrame,
    Y_train: pd.DataFrame,
    cv_results: Dict[str, Dict[str, Any]],
    *,
    model_names: Optional[List[str]] = None,
) -> Tuple[StandardScaler, Dict[str, Dict[str, Any]]]:
    """
    Fit StandardScaler on X_train; for each target and model, clone + set_params
    and fit. Scaled models use scaled X; trees use raw X.

    Returns (scaler_fitted_on_X_train, trained_estimators[target][model]).
    """
    mnames = model_names or list(get_models().keys())
    cfg = get_models()

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train.to_numpy(dtype=float))
    X_raw = X_train.to_numpy(dtype=float)

    trained: Dict[str, Dict[str, Any]] = {}

    for target in Y_train.columns:
        if target not in cv_results:
            raise KeyError(f"cv_results missing target {target!r}")
        trained[target] = {}
        y = Y_train[target].to_numpy(dtype=float)

        for mname in mnames:
            best = _coerce_params(mname, dict(cv_results[target][mname]["best_params"]))
            est = clone(cfg[mname]["model"])
            est.set_params(**best)

            if mname in NEEDS_SCALING:
                est.fit(X_scaled, y)
            else:
                est.fit(X_raw, y)

            trained[target][mname] = est

    return scaler, trained


def save_trained_bundle(
    scaler: StandardScaler,
    trained: Dict[str, Dict[str, Any]],
    out_dir: Path,
) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    joblib.dump(scaler, out_dir / "scaler.joblib")
    paths.append(out_dir / "scaler.joblib")

    for target, per_m in trained.items():
        tdir = out_dir / _safe_filename(target)
        tdir.mkdir(parents=True, exist_ok=True)
        for mname, est in per_m.items():
            fp = tdir / f"{_safe_filename(mname)}.joblib"
            joblib.dump(est, fp)
            paths.append(fp)
    return paths


def load_cv_results(path: Path) -> Dict[str, Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))
