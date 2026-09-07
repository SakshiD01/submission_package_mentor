"""Tests for raw ML FastAPI app (Task 7) + semantic routes (Task 12)."""

import pytest
from fastapi.testclient import TestClient

from ml_api import create_app
from ml_engine import PROJECT_ROOT
from semantic_api import register_semantic_routes


def _app_with_semantic(**kwargs):
    app = create_app(**kwargs)
    register_semantic_routes(app)
    return app


def test_health_503_when_no_models(tmp_path):
    app = create_app(models_root=tmp_path)
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["error"] == "model_not_ready"


@pytest.mark.integration
def test_health_200_when_models_present():
    reg = PROJECT_ROOT / "models" / "v1" / "registry.json"
    if not reg.is_file():
        pytest.skip("no trained models")
    app = _app_with_semantic()
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["model_version"] == "v1"
    assert "training_runs" in data
    assert data["phase1_models"] == 101
    assert data["phase2_models_pending"] == 35


@pytest.mark.integration
def test_predict_empty_body():
    reg = PROJECT_ROOT / "models" / "v1" / "registry.json"
    if not reg.is_file():
        pytest.skip("no trained models")
    app = _app_with_semantic()
    client = TestClient(app)
    r = client.post("/predict", json={})
    assert r.status_code == 200
    assert len(r.json()) == 136


@pytest.mark.integration
def test_predict_selective_unknown_output():
    reg = PROJECT_ROOT / "models" / "v1" / "registry.json"
    if not reg.is_file():
        pytest.skip("no trained models")
    app = _app_with_semantic()
    client = TestClient(app)
    r = client.post(
        "/predict/selective",
        json={"outputs": ["not_a_real_slug_xyz"], "VolAllPImGB": 1.0},
    )
    assert r.status_code == 422
    assert r.json()["error"] == "unknown_output"


@pytest.mark.integration
def test_outputs_and_inputs_lists():
    reg = PROJECT_ROOT / "models" / "v1" / "registry.json"
    if not reg.is_file():
        pytest.skip("no trained models")
    app = _app_with_semantic()
    client = TestClient(app)
    o = client.get("/outputs")
    assert o.status_code == 200
    assert len(o.json()) == 136
    i = client.get("/inputs")
    assert i.status_code == 200
    assert len(i.json()) == 153


SECTION_19_IMPORT = {
    "supplier_region": "great_britain",
    "origin_port": "liverpool",
    "destination_region": "ireland",
    "destination_port": "dublin",
    "commodity_type": "agri",
    "direction": "import",
    "product_volume_tonnes": 1643898,
    "route_type": "direct_gb",
    "check_regime": "hard",
    "customs_officers": 10,
    "dafm_officers": 33,
    "security_officers": 10,
    "tractors": 20,
    "shelf_life_days": 21,
    "unaccompanied_pct": 0.5,
    "doc_check_cost_eur": 50,
    "phy_check_cost_eur": 500,
    "sec_check_cost_eur": 500,
}


def test_scenario_options_without_models(tmp_path):
    app = _app_with_semantic(models_root=tmp_path)
    client = TestClient(app)
    r = client.get("/scenario/options")
    assert r.status_code == 200
    assert "supplier_region" in r.json()


def test_scenario_schema_without_models(tmp_path):
    app = _app_with_semantic(models_root=tmp_path)
    client = TestClient(app)
    r = client.get("/scenario/schema")
    assert r.status_code == 200
    body = r.json()
    assert "wizard_steps" in body
    assert "scenario_request_schema" in body


def test_scenario_predict_503_without_models(tmp_path):
    app = _app_with_semantic(models_root=tmp_path)
    client = TestClient(app)
    r = client.post("/scenario/predict", json=SECTION_19_IMPORT)
    assert r.status_code == 503
    assert r.json()["error"] == "model_not_ready"


def test_scenario_validate_without_models(tmp_path):
    app = _app_with_semantic(models_root=tmp_path)
    client = TestClient(app)
    r = client.post("/scenario/validate", json=SECTION_19_IMPORT)
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is True
    assert data["active_corridor"] == "IRE_GB"


def test_scenario_landbridge_400():
    reg = PROJECT_ROOT / "models" / "v1" / "registry.json"
    if not reg.is_file():
        pytest.skip("no trained models")
    bad = dict(SECTION_19_IMPORT)
    bad["route_type"] = "landbridge"
    app = _app_with_semantic()
    client = TestClient(app)
    r = client.post("/scenario/predict", json=bad)
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_input"


@pytest.mark.integration
def test_scenario_predict_section19_overall_confidence():
    reg = PROJECT_ROOT / "models" / "v1" / "registry.json"
    if not reg.is_file():
        pytest.skip("no trained models")
    app = _app_with_semantic()
    client = TestClient(app)
    r = client.post("/scenario/predict", json=SECTION_19_IMPORT)
    assert r.status_code == 200
    data = r.json()
    assert data["overall_confidence"] in ("high", "medium", "low")
    assert "results" in data
    assert data["check_regime"] == "hard"
    assert data["model_version"] == "v1"
