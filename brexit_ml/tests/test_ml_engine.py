"""Tests for MLEngine (Task 6)."""

from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.preprocessing import StandardScaler

from ml_engine import MLEngine, PROJECT_ROOT


class _DummyReg:
    def predict(self, X):
        return np.array([42.0])


def _minimal_registry(tmp_path, medians: dict) -> Path:
    """Tiny registry + scaler for unit tests without full xgboost."""
    mdir = tmp_path / "models" / "v1"
    mdir.mkdir(parents=True)
    X = np.zeros((5, 153))
    scaler = StandardScaler().fit(X)
    joblib.dump(scaler, mdir / "scaler_X.pkl")

    reg = {
        "version": "v1",
        "trained_at": "2020-01-01T00:00:00Z",
        "training_runs": 5,
        "input_features": 153,
        "output_targets": 2,
        "scaler": "scaler_X.pkl",
        "training_medians": medians,
        "outputs": {
            "out_a": {
                "raw_key": "Out A",
                "model_file": "model_out_a.pkl",
                "classifier_file": None,
                "phase": 1,
                "unit": "hours",
                "coverage_pct": 50,
                "model_type": "xgb_regressor",
                "r2_cv_mean": 0.9,
                "r2_cv_std": 0.04,
                "mae_cv_mean": 0.1,
                "zero_inflated": False,
            },
            "out_phase2": {
                "raw_key": "Out EU",
                "model_file": None,
                "classifier_file": None,
                "phase": 2,
                "unit": "hours",
                "coverage_pct": 5,
                "model_type": "not_trained",
                "r2_cv_mean": None,
                "r2_cv_std": None,
                "mae_cv_mean": None,
                "zero_inflated": False,
            },
        },
    }
    import json

    with open(mdir / "registry.json", "w", encoding="utf-8") as f:
        json.dump(reg, f)

    joblib.dump(_DummyReg(), mdir / "model_out_a.pkl")
    return tmp_path


def test_ml_engine_predict_dummy(tmp_path):
    from training_columns import TRAINING_COLUMN_ORDER

    medians = {c: 0.0 for c in TRAINING_COLUMN_ORDER}
    root = _minimal_registry(tmp_path, medians)
    eng = MLEngine("v1", models_root=root)
    out = eng.predict({})
    assert out["out_a"].value == 42.0
    assert out["out_a"].status == "ok"
    assert out["out_phase2"].status == "not_trained"
    assert out["out_phase2"].value is None


@pytest.mark.integration
def test_ml_engine_real_models_when_present():
    """Smoke test against ``models/v1`` from a real ``train.py`` run."""
    mdir = PROJECT_ROOT / "models" / "v1"
    if not (mdir / "registry.json").is_file():
        pytest.skip("no trained models")
    eng = MLEngine("v1", models_root=PROJECT_ROOT)
    preds = eng.predict({})
    assert len(preds) == 136
    phase2 = [p for p in preds.values() if p.status == "not_trained"]
    assert len(phase2) == 35
    okish = [p for p in preds.values() if p.status in ("ok", "low_coverage", "zero_predicted")]
    assert len(okish) == 101
