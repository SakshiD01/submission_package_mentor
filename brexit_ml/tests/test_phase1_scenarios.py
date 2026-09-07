"""Tests for Phase 1 scenario allow-list (Task 8, spec §19)."""

import pytest
from fastapi import HTTPException

from phase1_scenarios import validate_phase1_scenario
from schemas import ScenarioRequest


def _base_export(**kwargs):
    d = dict(
        supplier_region="ireland",
        origin_port="dublin",
        destination_region="great_britain",
        destination_port="liverpool",
        commodity_type="agri",
        direction="export",
        product_volume_tonnes=1000.0,
        route_type="direct_gb",
        check_regime="standard",
    )
    d.update(kwargs)
    return ScenarioRequest(**d)


def _base_import(**kwargs):
    d = dict(
        supplier_region="great_britain",
        origin_port="liverpool",
        destination_region="ireland",
        destination_port="dublin",
        commodity_type="agri",
        direction="import",
        product_volume_tonnes=1643898.0,
        route_type="direct_gb",
        check_regime="hard",
    )
    d.update(kwargs)
    return ScenarioRequest(**d)


def test_valid_section19_export_dublin_liverpool():
    validate_phase1_scenario(_base_export())


def test_valid_section19_export_rosslare_pembroke():
    validate_phase1_scenario(
        _base_export(
            origin_port="rosslare",
            destination_port="pembroke",
        )
    )


def test_valid_section19_import_gb_to_dublin():
    """§19 curl example: GB → Dublin import."""
    validate_phase1_scenario(_base_import())


def test_route_type_landbridge_raises():
    with pytest.raises(HTTPException) as ei:
        validate_phase1_scenario(_base_import(route_type="landbridge"))
    assert ei.value.status_code == 400
    assert ei.value.detail["error"] == "invalid_input"


def test_eu_supplier_raises():
    with pytest.raises(HTTPException) as ei:
        validate_phase1_scenario(
            _base_export(
                supplier_region="eu",
                origin_port="cherbourg",
                destination_port="liverpool",
            )
        )
    assert ei.value.status_code == 400


def test_inconsistent_ports_fishguard_to_dublin_import():
    """Fishguard pairs with Rosslare only in §19, not Dublin."""
    with pytest.raises(HTTPException) as ei:
        validate_phase1_scenario(
            _base_import(
                origin_port="fishguard",
                destination_port="dublin",
            )
        )
    assert ei.value.status_code == 400


def test_export_wrong_regions_raises():
    with pytest.raises(HTTPException) as ei:
        validate_phase1_scenario(
            _base_export(
                supplier_region="great_britain",
                destination_region="ireland",
            )
        )
    assert ei.value.status_code == 400


def test_import_wrong_edge_liverpool_to_rosslare():
    with pytest.raises(HTTPException) as ei:
        validate_phase1_scenario(
            _base_import(
                destination_port="rosslare",
            )
        )
    assert ei.value.status_code == 400
