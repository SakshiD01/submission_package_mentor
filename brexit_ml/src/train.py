"""
Offline training: scaler, per-output XGBoost (+ optional zero-inflation), registry (spec §5–6, §9).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

from data_loader import load_xlsx, save_processed_parquet
from training_columns import (
    OUTPUT_COLUMN_ORDER,
    TRAINING_COLUMN_ORDER,
    output_phase_index,
    validate_column_lists,
)

ZERO_INFLATION_THRESHOLD = 0.30

XGB_PARAMS = {
    "n_estimators": 300,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "objective": "reg:squarederror",
    "random_state": 42,
    "n_jobs": -1,
}

XGB_CLF_PARAMS = {
    "n_estimators": 300,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "objective": "binary:logistic",
    "random_state": 42,
    "n_jobs": -1,
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def col_to_slug(name: str) -> str:
    """Filesystem-safe slug for model filenames (spec §6)."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug[:80]


def infer_output_unit(raw_key: str) -> str:
    """Coarse unit label for registry / API (spec §11 groupings)."""
    k = raw_key.lower()
    if "cost" in k:
        return "EUR"
    if "queue" in k:
        return "trucks"
    if "utilisation" in k or "shelflife" in k or "remaining shelf" in k:
        return "fraction"
    return "hours"


def _nan_to_none(x: Any) -> Any:
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    if isinstance(x, dict):
        return {k: _nan_to_none(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_nan_to_none(v) for v in x]
    return x


def _cv_regressor(
    model: Any,
    X: np.ndarray,
    y: np.ndarray,
    cv: int = 5,
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Return mean/std R² and mean MAE; None if CV not possible."""
    n = len(y)
    if n < 2:
        return None, None, None
    cv_folds = min(cv, n)
    if cv_folds < 2:
        return None, None, None
    try:
        # sklearn/numpy may emit RuntimeWarning (e.g. nanvar ddof) during CV scoring
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            r2 = cross_val_score(model, X, y, cv=cv_folds, scoring="r2")
            mae = -cross_val_score(
                model, X, y, cv=cv_folds, scoring="neg_mean_absolute_error"
            )
            r2_ok = np.asarray(r2, dtype=float)[np.isfinite(r2)]
            mae_ok = np.asarray(mae, dtype=float)[np.isfinite(mae)]
            if r2_ok.size == 0:
                r2_m, r2_s = None, None
            else:
                r2_m = float(np.mean(r2_ok))
                r2_s = float(np.std(r2_ok, ddof=1)) if r2_ok.size >= 2 else None
            mae_m = float(np.mean(mae_ok)) if mae_ok.size > 0 else None
        return r2_m, r2_s, mae_m
    except Exception:
        return None, None, None


def _load_xy(
    xlsx_path: Path,
    processed_dir: Path,
    *,
    prefer_parquet: bool,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    xp = processed_dir / "X_train.parquet"
    yp = processed_dir / "Y_train.parquet"
    if prefer_parquet and xp.is_file() and yp.is_file():
        return pd.read_parquet(xp), pd.read_parquet(yp)
    if not xlsx_path.is_file():
        raise FileNotFoundError(
            f"No parquet at {processed_dir} and no workbook at {xlsx_path}. "
            "Place the AnyLogic export as data/raw/completed_runs.xlsx."
        )
    X, Y = load_xlsx(xlsx_path)
    save_processed_parquet(X, Y, processed_dir)
    return X, Y


def train_phase1_output(
    raw_key: str,
    y: np.ndarray,
    X_scaled: np.ndarray,
    models_dir: Path,
) -> Dict[str, Any]:
    """
    Train one Phase 1 target; return registry ``outputs`` entry and write model files.
    """
    from xgboost import XGBClassifier, XGBRegressor

    slug = col_to_slug(raw_key)
    coverage = float((y != 0).mean())
    coverage_pct = int(round(100 * coverage))
    unit = infer_output_unit(raw_key)
    phase = 1

    nonzeros = y != 0
    n_nz = int(nonzeros.sum())

    if n_nz == 0:
        clf = DummyClassifier(strategy="constant", constant=0)
        clf.fit(X_scaled, np.zeros(len(y), dtype=int))
        clf_path = models_dir / f"classifier_{slug}.pkl"
        joblib.dump(clf, clf_path)
        return {
            "raw_key": raw_key,
            "model_file": None,
            "classifier_file": clf_path.name,
            "phase": phase,
            "unit": unit,
            "coverage_pct": coverage_pct,
            "model_type": "zero_inflated_xgb",
            "r2_cv_mean": None,
            "r2_cv_std": None,
            "mae_cv_mean": None,
            "zero_inflated": True,
        }

    use_zi = coverage < ZERO_INFLATION_THRESHOLD
    y_binary = nonzeros.astype(int)

    reg_path = models_dir / f"model_{slug}.pkl"
    clf_path = models_dir / f"classifier_{slug}.pkl"

    if use_zi:
        clf = XGBClassifier(**XGB_CLF_PARAMS)
        clf.fit(X_scaled, y_binary)
        joblib.dump(clf, clf_path)

        X_r, y_r = X_scaled[nonzeros], y[nonzeros]
        reg = XGBRegressor(**XGB_PARAMS)
        reg.fit(X_r, y_r)
        joblib.dump(reg, reg_path)

        r2_m, r2_s, mae_m = _cv_regressor(
            XGBRegressor(**XGB_PARAMS), X_r, y_r
        )

        return {
            "raw_key": raw_key,
            "model_file": reg_path.name,
            "classifier_file": clf_path.name,
            "phase": phase,
            "unit": unit,
            "coverage_pct": coverage_pct,
            "model_type": "zero_inflated_xgb",
            "r2_cv_mean": r2_m,
            "r2_cv_std": r2_s,
            "mae_cv_mean": mae_m,
            "zero_inflated": True,
        }

    reg = XGBRegressor(**XGB_PARAMS)
    reg.fit(X_scaled, y)
    joblib.dump(reg, reg_path)

    r2_m, r2_s, mae_m = _cv_regressor(XGBRegressor(**XGB_PARAMS), X_scaled, y)

    return {
        "raw_key": raw_key,
        "model_file": reg_path.name,
        "classifier_file": None,
        "phase": phase,
        "unit": unit,
        "coverage_pct": coverage_pct,
        "model_type": "xgb_regressor",
        "r2_cv_mean": r2_m,
        "r2_cv_std": r2_s,
        "mae_cv_mean": mae_m,
        "zero_inflated": False,
    }


def phase2_registry_entry(raw_key: str, y: np.ndarray) -> Dict[str, Any]:
    """Phase 2 targets: no model files (spec §9)."""
    coverage = float((y != 0).mean())
    coverage_pct = int(round(100 * coverage))
    return {
        "raw_key": raw_key,
        "model_file": None,
        "classifier_file": None,
        "phase": 2,
        "unit": infer_output_unit(raw_key),
        "coverage_pct": coverage_pct,
        "model_type": "not_trained",
        "r2_cv_mean": None,
        "r2_cv_std": None,
        "mae_cv_mean": None,
        "zero_inflated": False,
    }


def run_training(
    *,
    xlsx_path: Path,
    processed_dir: Path,
    models_dir: Path,
    prefer_parquet: bool,
) -> Dict[str, Any]:
    validate_column_lists()
    processed_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    X_df, Y_df = _load_xy(xlsx_path, processed_dir, prefer_parquet=prefer_parquet)
    if X_df.shape[1] != 153 or Y_df.shape[1] != 136:
        raise ValueError(f"Bad shapes X={X_df.shape}, Y={Y_df.shape}")

    X = X_df[TRAINING_COLUMN_ORDER].astype(float).values
    medians = {c: float(X_df[c].median()) for c in TRAINING_COLUMN_ORDER}

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    joblib.dump(scaler, models_dir / "scaler_X.pkl")

    outputs_registry: Dict[str, Any] = {}
    warnings_list: List[str] = []

    for idx, raw_key in enumerate(OUTPUT_COLUMN_ORDER):
        phase = output_phase_index(idx)
        y = Y_df[raw_key].astype(float).values

        if phase == 2:
            slug = col_to_slug(raw_key)
            outputs_registry[slug] = phase2_registry_entry(raw_key, y)
            continue

        entry = train_phase1_output(raw_key, y, X_scaled, models_dir)
        slug = col_to_slug(raw_key)
        outputs_registry[slug] = entry

        r2 = entry.get("r2_cv_mean")
        if r2 is not None and r2 < 0.5:
            warnings_list.append(
                f"WARNING: R²_cv_mean < 0.5 for {raw_key!r} (slug={slug}, r2={r2:.3f})"
            )

    registry = {
        "version": models_dir.name,
        "trained_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "training_runs": int(len(X_df)),
        "input_features": 153,
        "output_targets": 136,
        "scaler": "scaler_X.pkl",
        "training_medians": medians,
        "outputs": outputs_registry,
    }

    reg_path = models_dir / "registry.json"
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(_nan_to_none(registry), f, indent=2)

    for w in warnings_list:
        print(w)

    return registry


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Brexit ML surrogate models.")
    parser.add_argument(
        "--xlsx",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw" / "completed_runs.xlsx",
        help="Source AnyLogic export",
    )
    parser.add_argument(
        "--processed",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed",
        help="Directory for parquet caches",
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=PROJECT_ROOT / "models" / "v1",
        help="Output directory for scaler, models, registry",
    )
    parser.add_argument(
        "--reload-xlsx",
        action="store_true",
        help="Ignore cached parquet and reload from --xlsx",
    )
    args = parser.parse_args()

    run_training(
        xlsx_path=args.xlsx,
        processed_dir=args.processed,
        models_dir=args.models_dir,
        prefer_parquet=not args.reload_xlsx,
    )
    print(f"Training complete. Registry: {args.models_dir / 'registry.json'}")


if __name__ == "__main__":
    main()
