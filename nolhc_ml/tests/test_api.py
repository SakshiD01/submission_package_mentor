"""API contract tests (nolhc_ml_engine_spec.md §16 Phase 1e)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ml_api import create_app  # noqa: E402
from ml_engine import MLEngine  # noqa: E402


def test_health_includes_stacking_won_count(minimal_models_root: Path) -> None:
    eng = MLEngine("v1", models_root=minimal_models_root)
    app = create_app(engine=eng)
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "stacking_won_count" in body
    assert body["stacking_won_count"] == 10
    assert body["output_models"] == 20


def test_predict_empty_body_19_outputs(minimal_models_root: Path) -> None:
    eng = MLEngine("v1", models_root=minimal_models_root)
    app = create_app(engine=eng)
    client = TestClient(app)
    r = client.post("/predict", json={})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 20
    assert all("value" in v and "r2" in v for v in data.values())


def test_predict_selective_two_outputs(minimal_models_root: Path) -> None:
    eng = MLEngine("v1", models_root=minimal_models_root)
    app = create_app(engine=eng)
    client = TestClient(app)
    r = client.post(
        "/predict/selective",
        json={"outputs": ["tt_ob_agri", "uti_cus_d"]},
    )
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == {"tt_ob_agri", "uti_cus_d"}


def test_benchmark_tt_ob_agri(minimal_models_root: Path) -> None:
    eng = MLEngine("v1", models_root=minimal_models_root)
    app = create_app(engine=eng)
    client = TestClient(app)
    r = client.get("/benchmark/tt_ob_agri")
    assert r.status_code == 200
    data = r.json()
    assert "winner" in data
    assert "stacking" in data
    assert "results" in data
    assert len(data["results"]) == 19


def test_predict_invalid_pct_returns_400(minimal_models_root: Path) -> None:
    eng = MLEngine("v1", models_root=minimal_models_root)
    app = create_app(engine=eng)
    client = TestClient(app)
    r = client.post("/predict", json={"Pct_A_IB_Red": 1.5})
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_input"


def test_model_not_ready_503(tmp_path: Path) -> None:
    app = create_app(model_version="v1", models_root=tmp_path)
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["error"] == "model_not_ready"
