"""Pytest path + minimal trained ``models/v1`` for API tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from candidate_models import CANDIDATE_MODELS  # noqa: E402
from training_columns import (  # noqa: E402
    OUTPUT_COLUMN_ORDER,
    OUTPUT_DESCRIPTIONS,
    TRAINING_COLUMN_ORDER,
    col_to_slug,
    output_unit,
)


@pytest.fixture
def minimal_models_root(tmp_path: Path) -> Path:
    """A complete ``models_root`` with ``v1/registry.json``, scaler, 20 models, 20 benchmarks."""
    vdir = tmp_path / "v1"
    vdir.mkdir(parents=True)
    rng = np.random.default_rng(42)
    n = 40
    x_raw = rng.standard_normal((n, len(TRAINING_COLUMN_ORDER)))
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x_raw)
    joblib.dump(scaler, vdir / "scaler_X.pkl")

    model_names = list(CANDIDATE_MODELS.keys())
    assert len(model_names) == 19

    registry_outputs: dict = {}
    medians = {c: float(np.median(x_raw[:, i])) for i, c in enumerate(TRAINING_COLUMN_ORDER)}

    for raw in OUTPUT_COLUMN_ORDER:
        slug = col_to_slug(raw)
        y = x_scaled[:, 0] * 0.5 + rng.standard_normal(n) * 0.05
        reg = Ridge(alpha=1.0).fit(x_scaled, y)
        joblib.dump(reg, vdir / f"model_{slug}.pkl")

        results = {}
        for i, mn in enumerate(model_names):
            results[mn] = {
                "r2_mean": 0.5 - i * 0.01,
                "r2_std": 0.02,
                "mae_mean": 0.1,
                "mae_std": 0.01,
                "status": "ok",
            }
        bench = {
            "output": raw,
            "slug": slug,
            "results": results,
            "stacking": {
                "r2_mean": 0.88,
                "r2_std": 0.03,
                "mae_mean": 0.05,
                "mae_std": 0.01,
                "base_learners": model_names[:5],
            },
            "winner": "stacking",
        }
        with open(vdir / f"benchmark_{slug}.json", "w", encoding="utf-8") as f:
            json.dump(bench, f)

        registry_outputs[slug] = {
            "raw_key": raw,
            "description": OUTPUT_DESCRIPTIONS.get(raw, raw),
            "unit": output_unit(raw),
            "registered_as": "stacking",
            "r2_cv_mean": 0.88,
            "mae_cv_mean": 0.05,
            "benchmark_file": f"benchmark_{slug}.json",
        }

    registry = {
        "version": "v1",
        "training_runs": n,
        "candidate_models_benchmarked": len(model_names),
        "stacking_won_count": 10,
        "training_medians": medians,
        "avg_r2_all_outputs": 0.85,
        "outputs": registry_outputs,
    }
    with open(vdir / "registry.json", "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
    return tmp_path
