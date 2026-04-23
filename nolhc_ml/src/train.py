"""
NOLHC training: benchmark 19 candidate models + stacking per output (nolhc_ml_engine_spec.md §8–9).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import StackingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_val_score
from sklearn.preprocessing import StandardScaler

from candidate_models import CANDIDATE_MODELS
from data_loader import (
    PROJECT_ROOT,
    append_runs_from_xlsx,
    load_data,
    load_parquet_pair,
)
from training_columns import (
    OUTPUT_COLUMN_ORDER,
    OUTPUT_DESCRIPTIONS,
    TRAINING_COLUMN_ORDER,
    col_to_slug,
    input_unit,
    output_unit,
)

CV_FOLDS = 5
STACK_TOP_K = 5
MODELS_ROOT = PROJECT_ROOT / "models"


def _confidence(r2: float) -> str:
    if r2 >= 0.90:
        return "high"
    if r2 >= 0.75:
        return "good"
    if r2 >= 0.50:
        return "low"
    return "poor"


def benchmark_models(
    X_scaled: np.ndarray,
    y: np.ndarray,
    cv: KFold,
) -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    for name, model in CANDIDATE_MODELS.items():
        try:
            cv_r2 = cross_val_score(model, X_scaled, y, cv=cv, scoring="r2", n_jobs=-1)
            cv_mae = cross_val_score(
                model, X_scaled, y, cv=cv, scoring="neg_mean_absolute_error", n_jobs=-1
            )
            results[name] = {
                "r2_mean": float(cv_r2.mean()),
                "r2_std": float(cv_r2.std()),
                "mae_mean": float(-cv_mae.mean()),
                "mae_std": float(cv_mae.std()),
                "status": "ok",
            }
        except Exception as e:  # noqa: BLE001
            results[name] = {
                "r2_mean": -999.0,
                "r2_std": 0.0,
                "mae_mean": 999.0,
                "mae_std": 0.0,
                "status": f"failed: {str(e)[:120]}",
            }
    return dict(sorted(results.items(), key=lambda x: x[1]["r2_mean"], reverse=True))


def build_stack_cv_results(
    benchmark_sorted: Dict[str, Dict[str, Any]],
    X_scaled: np.ndarray,
    y: np.ndarray,
    cv: KFold,
) -> Tuple[List[str], Dict[str, Any]]:
    ranked = [n for n, info in benchmark_sorted.items() if info["status"] == "ok"][:STACK_TOP_K]
    if len(ranked) < 2:
        return ranked, {
            "r2_mean": -999.0,
            "r2_std": 0.0,
            "mae_mean": 999.0,
            "mae_std": 0.0,
            "base_learners": ranked,
        }
    estimators = [(n, clone(CANDIDATE_MODELS[n])) for n in ranked]
    stack = StackingRegressor(
        estimators=estimators,
        final_estimator=Ridge(alpha=1.0),
        cv=5,
        passthrough=False,
        n_jobs=-1,
    )
    cv_r2 = cross_val_score(stack, X_scaled, y, cv=cv, scoring="r2", n_jobs=-1)
    cv_mae = cross_val_score(
        stack, X_scaled, y, cv=cv, scoring="neg_mean_absolute_error", n_jobs=-1
    )
    return ranked, {
        "r2_mean": float(cv_r2.mean()),
        "r2_std": float(cv_r2.std()),
        "mae_mean": float(-cv_mae.mean()),
        "mae_std": float(cv_mae.std()),
        "base_learners": ranked,
    }


def run_training(
    *,
    x_train: pd.DataFrame,
    y_train: pd.DataFrame,
    medians: Dict[str, float],
    version: str,
    models_root: Path = MODELS_ROOT,
) -> None:
    out_dir = models_root / version
    out_dir.mkdir(parents=True, exist_ok=True)

    scaler = StandardScaler()
    X_raw = x_train[TRAINING_COLUMN_ORDER].values.astype(np.float64)
    scaler.fit(X_raw)
    joblib.dump(scaler, out_dir / "scaler_X.pkl")
    X_scaled = scaler.transform(X_raw)

    cv = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=42)
    registry_outputs: Dict[str, Any] = {}
    stacking_wins = 0
    r2_list: List[float] = []

    for raw_out in OUTPUT_COLUMN_ORDER:
        slug = col_to_slug(raw_out)
        y = y_train[raw_out].values.astype(np.float64)

        bench = benchmark_models(X_scaled, y, cv)
        base_learners, stack_info = build_stack_cv_results(bench, X_scaled, y, cv)
        stack_r2 = stack_info["r2_mean"]

        ok_names = [k for k, v in bench.items() if v["status"] == "ok"]
        if not ok_names:
            raise RuntimeError(f"No successful benchmark for {raw_out}")
        best_ind_name = max(ok_names, key=lambda k: bench[k]["r2_mean"])
        best_ind_r2 = bench[best_ind_name]["r2_mean"]

        benchmark_payload = {
            "output": raw_out,
            "slug": slug,
            "results": bench,
            "stacking": {
                "r2_mean": stack_info["r2_mean"],
                "r2_std": stack_info["r2_std"],
                "mae_mean": stack_info["mae_mean"],
                "mae_std": stack_info["mae_std"],
                "base_learners": stack_info["base_learners"],
            },
        }

        if stack_r2 > best_ind_r2 and len(base_learners) >= 2:
            registered_as = "stacking"
            winner = "stacking"
            final = StackingRegressor(
                estimators=[(n, clone(CANDIDATE_MODELS[n])) for n in base_learners],
                final_estimator=Ridge(alpha=1.0),
                cv=5,
                passthrough=False,
                n_jobs=-1,
            )
            final.fit(X_scaled, y)
            r2_reg = stack_r2
            mae_reg = stack_info["mae_mean"]
            r2_std_reg = stack_info["r2_std"]
            stacking_wins += 1
        else:
            registered_as = best_ind_name
            winner = best_ind_name
            final = clone(CANDIDATE_MODELS[best_ind_name])
            final.fit(X_scaled, y)
            r2_reg = bench[best_ind_name]["r2_mean"]
            mae_reg = bench[best_ind_name]["mae_mean"]
            r2_std_reg = bench[best_ind_name]["r2_std"]

        benchmark_payload["winner"] = winner
        with open(out_dir / f"benchmark_{slug}.json", "w", encoding="utf-8") as f:
            json.dump(benchmark_payload, f, indent=2)

        joblib.dump(final, out_dir / f"model_{slug}.pkl")

        if len(base_learners) >= 2:
            stack_save = StackingRegressor(
                estimators=[(n, clone(CANDIDATE_MODELS[n])) for n in base_learners],
                final_estimator=Ridge(alpha=1.0),
                cv=5,
                passthrough=False,
                n_jobs=-1,
            )
            stack_save.fit(X_scaled, y)
        else:
            stack_save = clone(CANDIDATE_MODELS[best_ind_name])
            stack_save.fit(X_scaled, y)
        joblib.dump(stack_save, out_dir / f"stack_{slug}.pkl")

        r2_list.append(r2_reg)
        registry_outputs[slug] = {
            "raw_key": raw_out,
            "description": OUTPUT_DESCRIPTIONS.get(raw_out, raw_out),
            "unit": output_unit(raw_out),
            "model_file": f"model_{slug}.pkl",
            "stack_file": f"stack_{slug}.pkl",
            "benchmark_file": f"benchmark_{slug}.json",
            "registered_as": registered_as,
            "best_individual": best_ind_name,
            "best_individual_r2": float(best_ind_r2),
            "stack_r2_cv_mean": float(stack_r2),
            "r2_cv_mean": float(r2_reg),
            "r2_cv_std": float(r2_std_reg),
            "mae_cv_mean": float(mae_reg),
            "stack_base_learners": stack_info["base_learners"],
            "confidence": _confidence(r2_reg),
        }

    avg_r2 = float(np.mean(r2_list)) if r2_list else 0.0
    registry = {
        "version": version,
        "trained_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "training_runs": int(len(x_train)),
        "input_features": len(TRAINING_COLUMN_ORDER),
        "output_targets": len(OUTPUT_COLUMN_ORDER),
        "candidate_models_benchmarked": len(CANDIDATE_MODELS),
        "scaler": "scaler_X.pkl",
        "avg_r2_all_outputs": avg_r2,
        "stacking_won_count": stacking_wins,
        "training_medians": medians,
        "outputs": registry_outputs,
    }
    with open(out_dir / "registry.json", "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    print("\n=== NOLHC training summary ===")
    n_out = len(OUTPUT_COLUMN_ORDER)
    print(f"version={version} runs={len(x_train)} avg_R2={avg_r2:.4f} stacking_won={stacking_wins}/{n_out}\n")
    for raw_out in OUTPUT_COLUMN_ORDER:
        slug = col_to_slug(raw_out)
        o = registry_outputs[slug]
        warn = " ⚠ WARNING" if o["r2_cv_mean"] < 0.75 else ""
        print(
            f"{raw_out:22} | {o['registered_as']:14} | R2={o['r2_cv_mean']:.4f}±{o['r2_cv_std']:.4f} | "
            f"MAE={o['mae_cv_mean']:.4f} | stack_R2={o['stack_r2_cv_mean']:.4f}{warn}"
        )
    print(f"\nStacking won for {stacking_wins}/{n_out} outputs.")


def _next_version(models_root: Path) -> str:
    existing = []
    for p in models_root.iterdir():
        if p.is_dir() and p.name.startswith("v") and p.name[1:].isdigit():
            existing.append(int(p.name[1:]))
    n = max(existing, default=0) + 1
    return f"v{n}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Train NOLHC ML models")
    parser.add_argument("--xlsx", type=Path, default=PROJECT_ROOT / "data" / "raw" / "nolhc_runs.xlsx")
    parser.add_argument("--append", type=Path, default=None, help="Append runs from this xlsx then train")
    parser.add_argument("--version", type=str, default="v1", help="Model version directory under models/")
    parser.add_argument(
        "--no-expect-rows",
        action="store_true",
        help="Do not require exactly 129 rows (for small test datasets)",
    )
    parser.add_argument(
        "--from-parquet",
        action="store_true",
        help="Load X_train.parquet / Y_train.parquet instead of xlsx",
    )
    args = parser.parse_args()

    expect_rows = None if args.no_expect_rows else 129

    if args.append is not None:
        x_df, y_df, medians = append_runs_from_xlsx(args.append)
        version = _next_version(MODELS_ROOT)
        print(f"Appended runs; training new version {version} (n={len(x_df)})")
    elif args.from_parquet:
        x_df, y_df = load_parquet_pair()
        medians = {c: float(np.median(x_df[c].values)) for c in TRAINING_COLUMN_ORDER}
        version = args.version
    else:
        x_df, y_df, medians = load_data(args.xlsx, expect_rows=expect_rows, save=True)
        version = args.version

    run_training(x_train=x_df, y_train=y_df, medians=medians, version=version)


if __name__ == "__main__":
    main()
