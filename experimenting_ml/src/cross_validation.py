"""
Cross-validation on training set only for hyperparameter selection.

Supports:
- single KFold (e.g. 5-fold), or
- RepeatedKFold (e.g. 10-fold × 3 repeats = 30 validation scores per HP set),
  as recommended for small training sets (n ≈ 103).
"""

from __future__ import annotations

import time
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import KFold, ParameterGrid, RepeatedKFold
from sklearn.preprocessing import StandardScaler

from models import NEEDS_SCALING, get_models


def _approx_fit_calls_per_target(
    mnames: List[str],
    models_cfg: dict,
    n_folds: int,
) -> int:
    """Rough count of estimator.fit() calls for one target (all HP grids × folds)."""
    total = 0
    for mname in mnames:
        total += len(list(ParameterGrid(models_cfg[mname]["grid"]))) * n_folds
    return total


# Convergence noise during wide HP search
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def _mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(mean_absolute_error(y_true, y_pred))


def _make_cv_splitter(
    n_splits: int,
    *,
    n_repeats: int,
    random_state: int,
) -> Tuple[Any, int]:
    """
    Returns (splitter, n_expected_scores_per_param_set).
    n_repeats==1 → shuffled KFold; else RepeatedKFold.
    """
    if n_repeats < 1:
        raise ValueError("n_repeats must be >= 1")
    if n_repeats == 1:
        splitter = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
        return splitter, n_splits
    splitter = RepeatedKFold(
        n_splits=n_splits, n_repeats=n_repeats, random_state=random_state
    )
    return splitter, n_splits * n_repeats


def _cv_one_model_one_target(
    X_train: np.ndarray,
    y_train: np.ndarray,
    model_name: str,
    base_estimator,
    param_grid: List[dict],
    *,
    needs_scale: bool,
    n_splits: int = 5,
    n_repeats: int = 1,
    random_state: int = 42,
    collect_details: bool = False,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    splitter, n_expected = _make_cv_splitter(
        n_splits, n_repeats=n_repeats, random_state=random_state
    )
    grid = list(ParameterGrid(param_grid))

    best_mean = np.inf
    best_std = np.inf
    best_params: Optional[dict] = None
    best_fold_rmses: Optional[List[float]] = None
    detail_rows: List[Dict[str, Any]] = []

    for param_index, params in enumerate(grid, start=1):
        fold_rmses: List[float] = []
        fold_maes: List[float] = []
        failed = False
        for fold_idx, (train_idx, val_idx) in enumerate(splitter.split(X_train), start=1):
            X_tr, X_va = X_train[train_idx], X_train[val_idx]
            y_tr, y_va = y_train[train_idx], y_train[val_idx]

            if needs_scale:
                scaler = StandardScaler()
                X_tr_f = scaler.fit_transform(X_tr)
                X_va_f = scaler.transform(X_va)
            else:
                X_tr_f, X_va_f = X_tr, X_va

            est = clone(base_estimator)
            est.set_params(**params)
            try:
                est.fit(X_tr_f, y_tr)
                pred = est.predict(X_va_f)
                fold_rmse = _rmse(y_va, pred)
                fold_mae = _mae(y_va, pred)
                fold_rmses.append(fold_rmse)
                fold_maes.append(fold_mae)
                if collect_details:
                    detail_rows.append(
                        {
                            "model": model_name,
                            "param_index": param_index,
                            "params": dict(params),
                            "fold": fold_idx,
                            "rmse": fold_rmse,
                            "mae": fold_mae,
                            "n_train_fold": int(len(train_idx)),
                            "n_val_fold": int(len(val_idx)),
                        }
                    )
            except Exception:
                failed = True
                break

        if failed or len(fold_rmses) != n_expected:
            continue

        mean_rmse = float(np.mean(fold_rmses))
        std_rmse = float(np.std(fold_rmses))
        mean_mae = float(np.mean(fold_maes))
        std_mae = float(np.std(fold_maes))

        if collect_details:
            detail_rows.append(
                {
                    "model": model_name,
                    "param_index": param_index,
                    "params": dict(params),
                    "fold": "aggregate",
                    "rmse": mean_rmse,
                    "mae": mean_mae,
                    "std_rmse": std_rmse,
                    "std_mae": std_mae,
                    "n_train_fold": None,
                    "n_val_fold": None,
                }
            )

        if mean_rmse < best_mean or (
            np.isclose(mean_rmse, best_mean) and std_rmse < best_std
        ):
            best_mean = mean_rmse
            best_std = std_rmse
            best_params = dict(params)
            best_fold_rmses = fold_rmses

    if best_params is None or best_fold_rmses is None:
        raise RuntimeError(
            f"CV failed for model={model_name!r}: no successful parameter set."
        )

    result = {
        "best_params": best_params,
        "mean_rmse": best_mean,
        "std_rmse": best_std,
        "fold_rmses": best_fold_rmses,
        "fold_maes": None,
        "cv_n_splits": n_splits,
        "cv_n_repeats": n_repeats,
        "cv_n_scores": len(best_fold_rmses) if best_fold_rmses else 0,
    }
    # attach fold MAEs for selected best params
    for row in detail_rows:
        if (
            row["model"] == model_name
            and row["fold"] == "aggregate"
            and row["params"] == best_params
        ):
            result["mean_mae"] = row["mae"]
            result["std_mae"] = row["std_mae"]
            break
    return result, detail_rows


def run_cv_all(
    X_train: pd.DataFrame,
    Y_train: pd.DataFrame,
    target_names: Optional[List[str]] = None,
    model_names: Optional[List[str]] = None,
    *,
    n_splits: int = 5,
    n_repeats: int = 1,
    random_state: int = 42,
    verbose: bool = True,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    models_cfg = get_models()
    targets = target_names or list(Y_train.columns)
    mnames = model_names or list(models_cfg.keys())

    n_folds = n_splits * n_repeats
    n_pairs = len(targets) * len(mnames)
    approx_fits = _approx_fit_calls_per_target(mnames, models_cfg, n_folds) * len(
        targets
    )
    if verbose:
        print(
            f"CV: {len(targets)} target(s) × {len(mnames)} models = {n_pairs} runs; "
            f"~{approx_fits:,} estimator.fit() calls ({n_splits}-fold × {n_repeats} repeats).",
            flush=True,
        )

    X_np = X_train.to_numpy(dtype=float)
    cv_results: Dict[str, Dict[str, Dict[str, Any]]] = {}
    done = 0

    for tname in targets:
        cv_results[tname] = {}
        y_np = Y_train[tname].to_numpy(dtype=float)
        for mname in mnames:
            done += 1
            if verbose:
                print(
                    f"  [{done}/{n_pairs}] {tname} / {mname} …",
                    flush=True,
                )
            t0 = time.perf_counter()
            cfg = models_cfg[mname]
            result, _detail = _cv_one_model_one_target(
                X_np,
                y_np,
                mname,
                cfg["model"],
                cfg["grid"],
                needs_scale=mname in NEEDS_SCALING,
                n_splits=n_splits,
                n_repeats=n_repeats,
                random_state=random_state,
            )
            cv_results[tname][mname] = result
            if verbose:
                dt = time.perf_counter() - t0
                print(
                    f"      → mean_cv_rmse={result['mean_rmse']:.6f} ({dt:.1f}s)",
                    flush=True,
                )
    return cv_results


def run_cv_all_with_details(
    X_train: pd.DataFrame,
    Y_train: pd.DataFrame,
    target_names: Optional[List[str]] = None,
    model_names: Optional[List[str]] = None,
    *,
    n_splits: int = 5,
    n_repeats: int = 1,
    random_state: int = 42,
    verbose: bool = True,
) -> Tuple[Dict[str, Dict[str, Dict[str, Any]]], List[Dict[str, Any]]]:
    models_cfg = get_models()
    targets = target_names or list(Y_train.columns)
    mnames = model_names or list(models_cfg.keys())

    n_folds = n_splits * n_repeats
    n_pairs = len(targets) * len(mnames)
    approx_fits = _approx_fit_calls_per_target(mnames, models_cfg, n_folds) * len(
        targets
    )
    if verbose:
        print(
            f"CV (with fold details): {len(targets)} target(s) × {len(mnames)} models; "
            f"~{approx_fits:,} fit calls. This is slower than default CV.",
            flush=True,
        )

    X_np = X_train.to_numpy(dtype=float)
    cv_results: Dict[str, Dict[str, Dict[str, Any]]] = {}
    detail_rows_all: List[Dict[str, Any]] = []
    done = 0

    for tname in targets:
        cv_results[tname] = {}
        y_np = Y_train[tname].to_numpy(dtype=float)
        for mname in mnames:
            done += 1
            if verbose:
                print(f"  [{done}/{n_pairs}] {tname} / {mname} …", flush=True)
            t0 = time.perf_counter()
            cfg = models_cfg[mname]
            result, detail_rows = _cv_one_model_one_target(
                X_np,
                y_np,
                mname,
                cfg["model"],
                cfg["grid"],
                needs_scale=mname in NEEDS_SCALING,
                n_splits=n_splits,
                n_repeats=n_repeats,
                random_state=random_state,
                collect_details=True,
            )
            cv_results[tname][mname] = result
            if verbose:
                dt = time.perf_counter() - t0
                print(
                    f"      → mean_cv_rmse={result['mean_rmse']:.6f} ({dt:.1f}s)",
                    flush=True,
                )
            for r in detail_rows:
                r2 = dict(r)
                r2["target"] = tname
                detail_rows_all.append(r2)
    return cv_results, detail_rows_all
