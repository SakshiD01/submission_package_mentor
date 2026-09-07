"""Tests for output_filter (spec §18, plan Task 10)."""

from output_filter import OUTPUT_FILTER_FALLBACK, OUTPUT_FILTER_MAP, outputs_for_scenario


def test_agri_import_dublin_liverpool_matches_spec():
    """§18 verbatim list for (agri, import, direct_gb, dublin, liverpool)."""
    expected = [
        "Transportation time agri import from GB",
        "Agri avg WT on im at D",
        "Agri doc chk WT on im at D",
        "Agri phy chk WT on im at D",
        "Agri sec chk WT on im at D",
        "Agri avg waiting time on im at liv",
        "Remaining shelflife cat import from GB",
        "DDAFM insp bay utilisation",
        "D tractor utilisation",
        "D security post utilisation",
        "Trucks vessel queue length liv to D",
        "Liv DAFM insp bay utilisation",
        "Liv security post utilisation",
        "Total doc check cost im trucks to D",
        "Total phy check cost im trucks to D",
        "Total sec check cost im trucks to D",
    ]
    key = ("agri", "import", "direct_gb", "dublin", "liverpool")
    assert OUTPUT_FILTER_MAP[key] == expected
    assert outputs_for_scenario(*key) == expected


def test_agri_import_dublin_holyhead_matches_spec():
    """§18 verbatim list for holyhead."""
    expected = [
        "Transportation time agri import from GB",
        "Agri avg WT on im at D",
        "Agri doc chk WT on im at D",
        "Agri phy chk WT on im at D",
        "Agri sec chk WT on im at D",
        "Agri avg waiting time on im at holy",
        "Remaining shelflife cat import from GB",
        "DDAFM insp bay utilisation",
        "D tractor utilisation",
        "Trucks vessel queue length holy to D",
        "Holy DAFM insp bay utilisation",
        "Holy security post utilisation",
        "Total doc check cost im trucks to D",
        "Total phy check cost im trucks to D",
    ]
    key = ("agri", "import", "direct_gb", "dublin", "holyhead")
    assert OUTPUT_FILTER_MAP[key] == expected


def test_agri_export_dublin_liverpool_matches_spec():
    expected = [
        "Transportation time agri exportto GB",
        "Agri cus int WT on ex at D",
        "Remaining shelflife cat exportto GB",
        "D custom shed utilisation",
        "Trucks vessel queue length D to UK",
        "Total doc check cost ex trucks from IR to GBW",
        "Total phy check cost ex trucks from IR to GBW",
        "Total sec check cost ex trucks from IR to GBW",
    ]
    key = ("agri", "export", "direct_gb", "dublin", "liverpool")
    assert OUTPUT_FILTER_MAP[key] == expected


def test_all_products_import_dublin_liverpool_matches_spec():
    expected = [
        "Transportation time all P import from GB",
        "AP avg WT on im at D",
        "AP doc chk WT on im at D",
        "AP phy chk WT on im at D",
        "AP sec chk WT on im at D",
        "AP avg waiting time on im at liv",
        "DDAFM insp bay utilisation",
        "D tractor utilisation",
        "D security post utilisation",
        "Trucks vessel queue length liv to D",
        "Liv DAFM insp bay utilisation",
        "Total doc check cost im trucks to D",
        "Total phy check cost im trucks to D",
    ]
    key = ("all_products", "import", "direct_gb", "dublin", "liverpool")
    assert OUTPUT_FILTER_MAP[key] == expected


def test_phase1_section19_tuple_keys():
    """All §19 (irish, gb) pairs × commodities × directions × direct_gb."""
    assert len(OUTPUT_FILTER_MAP) == 30
    dublin_pairs = [("dublin", g) for g in ("liverpool", "holyhead", "heysham")]
    rosslare_pairs = [("rosslare", g) for g in ("fishguard", "pembroke")]
    for irish, gb in dublin_pairs + rosslare_pairs:
        for commodity in ("all_products", "agri", "category"):
            for direction in ("import", "export"):
                k = (commodity, direction, "direct_gb", irish, gb)
                assert k in OUTPUT_FILTER_MAP
                assert len(OUTPUT_FILTER_MAP[k]) >= 1


def test_outputs_for_scenario_unknown_fallback():
    key = ("agri", "import", "landbridge", "dublin", "liverpool")
    assert outputs_for_scenario(*key) == list(OUTPUT_FILTER_FALLBACK["agri"])
