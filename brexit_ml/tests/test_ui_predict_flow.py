"""
Integration: semantic predict returns the structure the UI expects (KPI cards + timeline).

This mirrors the browser flow after filling required Phase 1 fields and clicking Run Simulation.
"""

import pytest
from fastapi.testclient import TestClient

from ml_api import create_app
from ml_engine import PROJECT_ROOT
from semantic_api import register_semantic_routes

MIN_PHASE1_IMPORT = {
    "supplier_region": "great_britain",
    "origin_port": "liverpool",
    "destination_region": "ireland",
    "destination_port": "dublin",
    "commodity_type": "all_products",
    "direction": "import",
    "product_volume_tonnes": 100,
    "route_type": "direct_gb",
    "check_regime": "standard",
}


def _app():
    app = create_app()
    register_semantic_routes(app)
    return app


@pytest.mark.integration
def test_scenario_predict_response_shape_for_ui():
    """POST /scenario/predict returns ScenarioResponse fields the UI reads (results, KPI objects)."""
    reg = PROJECT_ROOT / "models" / "v1" / "registry.json"
    if not reg.is_file():
        pytest.skip("no trained models")
    client = TestClient(_app())
    r = client.post("/scenario/predict", json=MIN_PHASE1_IMPORT)
    assert r.status_code == 200, r.text
    data = r.json()

    for key in (
        "scenario_id",
        "corridor",
        "commodity",
        "direction",
        "check_regime",
        "model_version",
        "results",
        "warnings",
        "overall_confidence",
    ):
        assert key in data, f"missing top-level key {key!r}"

    assert data["direction"] == "import"
    assert data["commodity"] == "all_products"
    assert isinstance(data["results"], dict)

    nonempty_groups = [
        (gid, obj)
        for gid, obj in data["results"].items()
        if isinstance(obj, dict) and len(obj) > 0
    ]
    assert nonempty_groups, "expected at least one non-empty results group for the UI"

    required_pr_keys = ("unit", "status", "phase", "coverage_pct")
    for _gid, group in nonempty_groups:
        for _kpi_name, pr in group.items():
            assert isinstance(pr, dict), f"KPI {_kpi_name!r} should be an object"
            for k in required_pr_keys:
                assert k in pr, f"KPI {_kpi_name!r} missing {k!r} (UI formatPredictionValue / cards need this)"

    assert data["overall_confidence"] in ("high", "medium", "low")
