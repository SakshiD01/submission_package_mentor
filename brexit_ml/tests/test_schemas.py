"""Tests for Pydantic schemas (Task 2)."""

import pytest
from pydantic import ValidationError

from schemas import (
    ErrorResponse,
    PredictionResult,
    ScenarioRequest,
    ScenarioResponse,
    VALID_OPTIONS,
)


def test_scenario_request_section_19_example_validates():
    """Spec §19 curl: GB → IRE agri import Dublin, hard Brexit."""
    payload = {
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
    req = ScenarioRequest.model_validate(payload)
    assert req.origin_port == "liverpool"
    assert req.destination_port == "dublin"
    assert req.route_type == "direct_gb"


def test_scenario_request_invalid_enum_rejected():
    with pytest.raises(ValidationError) as excinfo:
        ScenarioRequest.model_validate(
            {
                "supplier_region": "great_britain",
                "origin_port": "liverpool",
                "destination_region": "ireland",
                "destination_port": "dublin",
                "commodity_type": "agri",
                "direction": "import",
                "product_volume_tonnes": 100.0,
                "route_type": "not_a_route",  # type: ignore[dict-item]
                "check_regime": "hard",
            }
        )
    assert "route_type" in str(excinfo.value).lower()


def test_prediction_result_and_scenario_response_round_trip():
    pr = PredictionResult(
        value=16.9,
        unit="hours",
        status="ok",
        phase=1,
        coverage_pct=23,
        r2=0.87,
    )
    data = pr.model_dump()
    assert PredictionResult.model_validate(data).value == 16.9

    sr = ScenarioResponse(
        scenario_id="test",
        corridor="Ireland → Great Britain",
        commodity="agri",
        direction="import",
        check_regime="hard",
        model_version="v1",
        results={
            "transit": {
                "Transportation time agri import from GB": {
                    "value": 16.9,
                    "unit": "hours",
                    "status": "ok",
                    "phase": 1,
                    "coverage_pct": 23,
                    "r2": 0.87,
                }
            }
        },
        warnings=[],
        overall_confidence="high",
    )
    dumped = sr.model_dump()
    assert ScenarioResponse.model_validate(dumped).scenario_id == "test"


def test_error_response():
    err = ErrorResponse(error="invalid_input", detail="volume must be positive")
    assert err.model_dump() == {"error": "invalid_input", "detail": "volume must be positive"}


def test_valid_options_shape():
    assert VALID_OPTIONS["supplier_region"] == ["ireland", "great_britain", "eu"]
    assert "dublin" in VALID_OPTIONS["origin_port"]["ireland"]  # type: ignore[index]
