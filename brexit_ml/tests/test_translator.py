"""Tests for param_translator (spec §15, §25 checklist)."""

from schemas import ScenarioRequest
from param_translator import baseline_medians_for_tests, translate


def _export_dublin_liverpool(**kwargs):
    d = dict(
        supplier_region="ireland",
        origin_port="dublin",
        destination_region="great_britain",
        destination_port="liverpool",
        commodity_type="agri",
        direction="export",
        product_volume_tonnes=42_000.0,
        route_type="direct_gb",
        check_regime="standard",
    )
    d.update(kwargs)
    return ScenarioRequest(**d)


def test_vol_zeroing_agri_export_liverpool():
    """§25: Ireland/Dublin/agri/export/Liverpool — only VolAgriExGB set, all other Vol* 0."""
    req = _export_dublin_liverpool()
    med = baseline_medians_for_tests()
    out = translate(req, med)
    for k, v in out.items():
        if not k.startswith("Vol"):
            continue
        if k == "VolAgriExGB":
            assert v == 42_000.0
        else:
            assert v == 0.0, k


def test_hard_agri_phy_pct():
    """§25: hard + agri → PerPhyChkAgriImIR == 0.3 (spec §16)."""
    req = _export_dublin_liverpool(check_regime="hard")
    out = translate(req, baseline_medians_for_tests())
    assert out["PerPhyChkAgriImIR"] == 0.3


def test_destination_holyhead_routing_splits():
    """§25: destination holyhead → PerProductMoveHoly==1, PerProductMoveLiv==0."""
    req = _export_dublin_liverpool(destination_port="holyhead")
    out = translate(req, baseline_medians_for_tests())
    assert out["PerProductMoveHoly"] == 1.0
    assert out["PerProductMoveLiv"] == 0.0


def test_import_gb_to_dublin_uses_liverpool_routing():
    """Import leg: GB port is origin — same PerProductMove* as export-to-Liverpool."""
    req = ScenarioRequest(
        supplier_region="great_britain",
        origin_port="liverpool",
        destination_region="ireland",
        destination_port="dublin",
        commodity_type="agri",
        direction="import",
        product_volume_tonnes=100.0,
        route_type="direct_gb",
        check_regime="standard",
    )
    out = translate(req, baseline_medians_for_tests())
    assert out["PerProductMoveLiv"] == 1.0
    assert out["PerProductMoveHoly"] == 0.0
    assert out["VolAgriImGB"] == 100.0
    assert out["DToLivVesselCap"] == 123.0
