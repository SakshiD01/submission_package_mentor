"""
Semantic output allow-list per scenario (spec §18).

Keys are ``(commodity_type, direction, route_type, irish_port, gb_port)`` for Phase 1
IRE↔GB. Display names match ``training_columns.OUTPUT_COLUMN_ORDER`` strings exactly.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from training_columns import OUTPUT_COLUMN_ORDER

ScenarioOutputKey = Tuple[str, str, str, str, str]

# --- Fallback (spec §18) --------------------------------------------------------

OUTPUT_FILTER_FALLBACK: Dict[str, List[str]] = {
    "agri": [
        "Transportation time agri import from GB",
        "Transportation time agri exportto GB",
        "Agri avg WT on im at D",
        "Agri phy chk WT on im at D",
        "Remaining shelflife cat import from GB",
        "DDAFM insp bay utilisation",
        "D tractor utilisation",
        "Trucks vessel queue length D to UK",
    ],
    "all_products": [
        "Transportation time all P import from GB",
        "Transportation time all P exportto GB",
        "AP avg WT on im at D",
        "DDAFM insp bay utilisation",
        "Trucks vessel queue length D to UK",
    ],
    "category": [
        "Transportation time cat import from GB",
        "Transportation time cat exportto GB",
        "Cat avg WT on im at D",
        "Remaining shelflife cat import from GB",
        "DDAFM insp bay utilisation",
    ],
}

_GB_SHORT = {
    "liverpool": "liv",
    "holyhead": "holy",
    "heysham": "hey",
    "fishguard": "fish",
    "pembroke": "pem",
}

_GB_UTIL = {
    "liverpool": "Liv",
    "holyhead": "Holy",
    "heysham": "Hey",
    "fishguard": "Fish",
    "pembroke": "Pem",
}


def _prefix(commodity: str) -> str:
    return {"all_products": "AP", "agri": "Agri", "category": "Cat"}[commodity]


def _transport_import(commodity: str) -> str:
    return {
        "all_products": "Transportation time all P import from GB",
        "agri": "Transportation time agri import from GB",
        "category": "Transportation time cat import from GB",
    }[commodity]


def _transport_export(commodity: str) -> str:
    return {
        "all_products": "Transportation time all P exportto GB",
        "agri": "Transportation time agri exportto GB",
        "category": "Transportation time cat exportto GB",
    }[commodity]


def _dublin_import(gb: str, commodity: str) -> List[str]:
    """Dublin × Liverpool / Holyhead / Heysham (import to Ireland)."""
    p = _prefix(commodity)
    short = _GB_SHORT[gb]
    gl = _GB_UTIL[gb]
    t = _transport_import(commodity)

    rows: List[str] = [
        t,
        f"{p} avg WT on im at D",
        f"{p} doc chk WT on im at D",
        f"{p} phy chk WT on im at D",
        f"{p} sec chk WT on im at D",
        f"{p} avg waiting time on im at {short}",
    ]
    if commodity != "all_products":
        rows.append("Remaining shelflife cat import from GB")
    rows.extend(
        [
            "DDAFM insp bay utilisation",
            "D tractor utilisation",
        ]
    )
    if gb == "liverpool":
        rows.append("D security post utilisation")
    rows.append(f"Trucks vessel queue length {short} to D")
    rows.append(f"{gl} DAFM insp bay utilisation")
    # §18 all_products + Liverpool omits GB security util; agri/category include it.
    if not (gb == "liverpool" and commodity == "all_products"):
        rows.append(f"{gl} security post utilisation")
    if gb == "liverpool" and commodity == "all_products":
        rows.extend(
            [
                "Total doc check cost im trucks to D",
                "Total phy check cost im trucks to D",
            ]
        )
    elif gb == "liverpool":
        rows.extend(
            [
                "Total doc check cost im trucks to D",
                "Total phy check cost im trucks to D",
                "Total sec check cost im trucks to D",
            ]
        )
    else:
        rows.extend(
            [
                "Total doc check cost im trucks to D",
                "Total phy check cost im trucks to D",
            ]
        )
    return rows


def _rosslare_import(gb: str, commodity: str) -> List[str]:
    """Rosslare × Fishguard / Pembroke (import to Ireland)."""
    p = _prefix(commodity)
    short = _GB_SHORT[gb]
    gl = _GB_UTIL[gb]
    t = _transport_import(commodity)

    rows: List[str] = [
        t,
        f"{p} avg WT on im at R",
        f"{p} doc chk WT on im at R",
        f"{p} phy chk WT on im at R",
        f"{p} sec chk WT on im at R",
        f"{p} avg waiting time on im at {short}",
    ]
    if commodity != "all_products":
        rows.append("Remaining shelflife cat import from GB")
    rows.extend(
        [
            "RDAFM insp bay utilisation",
            "R tractor utilisation",
            "R security post utilisation",
            f"Trucks vessel queue length {short} to R",
            f"{gl} DAFM insp bay utilisation",
            f"{gl} security post utilisation",
        ]
    )
    if commodity == "all_products":
        rows.extend(
            [
                "Total doc check cost im trucks to R",
                "Total phy check cost im trucks to R",
            ]
        )
    else:
        rows.extend(
            [
                "Total doc check cost im trucks to R",
                "Total phy check cost im trucks to R",
                "Total sec check cost im trucks to R",
            ]
        )
    return rows


def _dublin_export(_gb: str, commodity: str) -> List[str]:
    """Export from Dublin — same KPI set for Liverpool / Holyhead / Heysham (spec §18)."""
    p = _prefix(commodity)
    return [
        _transport_export(commodity),
        f"{p} cus int WT on ex at D",
        "Remaining shelflife cat exportto GB",
        "D custom shed utilisation",
        "Trucks vessel queue length D to UK",
        "Total doc check cost ex trucks from IR to GBW",
        "Total phy check cost ex trucks from IR to GBW",
        "Total sec check cost ex trucks from IR to GBW",
    ]


def _rosslare_export(_gb: str, commodity: str) -> List[str]:
    """Export from Rosslare — Irish leg uses R (spec OUTPUT_COLUMN_ORDER)."""
    p = _prefix(commodity)
    return [
        _transport_export(commodity),
        f"{p} avg WT on ex at R",
        "Remaining shelflife cat exportto GB",
        "R custom shed utilisation",
        "Trucks vessel queue length R to UK",
        "Total doc check cost ex trucks from IR to GBW",
        "Total phy check cost ex trucks from IR to GBW",
        "Total sec check cost ex trucks from IR to GBW",
    ]


def _build_output_filter_map() -> Dict[ScenarioOutputKey, List[str]]:
    m: Dict[ScenarioOutputKey, List[str]] = {}
    for commodity in ("all_products", "agri", "category"):
        for direction in ("import", "export"):
            for irish, gb_list in (
                ("dublin", ("liverpool", "holyhead", "heysham")),
                ("rosslare", ("fishguard", "pembroke")),
            ):
                for gb in gb_list:
                    key: ScenarioOutputKey = (commodity, direction, "direct_gb", irish, gb)
                    if irish == "dublin":
                        m[key] = _dublin_import(gb, commodity) if direction == "import" else _dublin_export(gb, commodity)
                    else:
                        m[key] = _rosslare_import(gb, commodity) if direction == "import" else _rosslare_export(gb, commodity)
    return m


OUTPUT_FILTER_MAP: Dict[ScenarioOutputKey, List[str]] = _build_output_filter_map()

_OUTPUT_SET = frozenset(OUTPUT_COLUMN_ORDER)


def validate_filter_map() -> None:
    """Assert every name in OUTPUT_FILTER_MAP / FALLBACK exists in OUTPUT_COLUMN_ORDER."""
    for _k, names in OUTPUT_FILTER_MAP.items():
        for n in names:
            if n not in _OUTPUT_SET:
                raise ValueError(f"Unknown output display name in filter map: {n!r}")
    for names in OUTPUT_FILTER_FALLBACK.values():
        for n in names:
            if n not in _OUTPUT_SET:
                raise ValueError(f"Unknown output display name in fallback: {n!r}")


validate_filter_map()


def outputs_for_scenario(
    commodity_type: str,
    direction: str,
    route_type: str,
    irish_port: str,
    gb_port: str,
) -> List[str]:
    """
    Return ordered display names to include for a semantic scenario.

    Unknown combinations fall back to commodity-only defaults (spec §18).
    """
    key = (commodity_type, direction, route_type, irish_port, gb_port)
    if key in OUTPUT_FILTER_MAP:
        return list(OUTPUT_FILTER_MAP[key])
    return list(OUTPUT_FILTER_FALLBACK.get(commodity_type, OUTPUT_FILTER_FALLBACK["agri"]))
