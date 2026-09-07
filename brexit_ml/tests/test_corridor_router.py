"""Light tests for corridor_router (plan Task 11)."""

from corridor_router import active_corridor_from_inputs, corridor_for_vol_key, nonzero_vol_keys


def test_no_volume_returns_none():
    assert active_corridor_from_inputs({}) == "none"
    assert active_corridor_from_inputs({"VolAgriExGB": 0.0}) == "none"
    assert active_corridor_from_inputs({"VolAgriExGB": 1e-12}) == "none"


def test_single_ire_gb_direct():
    d = {"VolAgriExGB": 1_000_000.0, "VolAllPImEULB": 0.0}
    assert active_corridor_from_inputs(d) == "ire_gb_direct"
    assert corridor_for_vol_key("VolAgriExGB") == "ire_gb_direct"


def test_mixed_corridors():
    d = {"VolAgriExGB": 100.0, "VolAllPImEULB": 50.0}
    assert active_corridor_from_inputs(d) == "mixed_corridors"


def test_landbridge_only():
    assert active_corridor_from_inputs({"VolAgriImEULB": 1.0}) == "eu_landbridge"


def test_nonzero_vol_keys_sorted():
    assert nonzero_vol_keys({"VolB": 1, "VolA": 2}) == ["VolA", "VolB"]
