"""
Semantic ScenarioRequest → 153 raw training inputs (spec §15–17).

Phase 1 (direct_gb IRE↔GB): routing uses the GB port on the active leg — on **export**
that is `destination_port`; on **import** it is `origin_port`. Vessel-cap lookup follows
the same leg (`VESSEL_CAP_MAP[irish][gb]` in either direction). Resources attach to the
Irish port (`origin_port` on export, `destination_port` on import), per v1 freeze.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from schemas import ScenarioRequest
from training_columns import TRAINING_COLUMN_ORDER

# --- Volume (spec §15) --------------------------------------------------------

VOLUME_MAP: Dict[Tuple[str, str, str], str] = {
    ("all_products", "import", "direct_gb"): "VolAllPImGB",
    ("all_products", "export", "direct_gb"): "VolAllPExGB",
    ("agri", "import", "direct_gb"): "VolAgriImGB",
    ("agri", "export", "direct_gb"): "VolAgriExGB",
    ("category", "import", "direct_gb"): "VolCatImGB",
    ("category", "export", "direct_gb"): "VolCatExGB",
    ("all_products", "import", "landbridge"): "VolAllPImEULB",
    ("all_products", "export", "landbridge"): "VolAllPExEULB",
    ("agri", "import", "landbridge"): "VolAgriImEULB",
    ("agri", "export", "landbridge"): "VolAgriExEULB",
    ("all_products", "import", "direct_cherbourg"): "VolAllPImViaChe",
    ("all_products", "export", "direct_cherbourg"): "VolAllPExViaChe",
    ("agri", "import", "direct_cherbourg"): "VolAgriImViaChe",
    ("agri", "export", "direct_cherbourg"): "VolAgriExViaChe",
    ("all_products", "import", "direct_rotterdam"): "VolAllPImViaRott",
    ("all_products", "export", "direct_rotterdam"): "VolAllPExViaRott",
    ("agri", "import", "direct_rotterdam"): "VolAgriImViaRott",
    ("agri", "export", "direct_rotterdam"): "VolAgriExViaRott",
    ("all_products", "import", "direct_zeebrugge"): "VolAllPImViaZee",
    ("all_products", "export", "direct_zeebrugge"): "VolAllPExViaZee",
    ("agri", "import", "direct_zeebrugge"): "VolAgriImViaZee",
    ("agri", "export", "direct_zeebrugge"): "VolAgriExViaZee",
}

# --- Port routing (spec §17) ---------------------------------------------------

_INTERNAL_PORT_ROUTING_KEYS = frozenset({"vessel_cap_param", "vessel_cap"})

PORT_ROUTING: Dict[str, Dict[str, Any]] = {
    "liverpool": {
        "PerProductMoveLiv": 1.0,
        "PerProductMoveHoly": 0.0,
        "PerProductMoveHey": 0.0,
        "PerProductMoveFish": 0.0,
        "PerProductMovePem": 0.0,
        "vessel_cap_param": "DToLivVesselCap",
        "vessel_cap": 123,
    },
    "holyhead": {
        "PerProductMoveHoly": 1.0,
        "PerProductMoveLiv": 0.0,
        "PerProductMoveHey": 0.0,
        "PerProductMoveFish": 0.0,
        "PerProductMovePem": 0.0,
        "vessel_cap_param": "DToHolyVesselCap",
        "vessel_cap": 209,
    },
    "heysham": {
        "PerProductMoveHey": 1.0,
        "PerProductMoveLiv": 0.0,
        "PerProductMoveHoly": 0.0,
        "PerProductMoveFish": 0.0,
        "PerProductMovePem": 0.0,
        "vessel_cap_param": "DToHeyVesselCap",
        "vessel_cap": 122,
    },
    "fishguard": {
        "PerProductMoveFish": 1.0,
        "PerProductMoveLiv": 0.0,
        "PerProductMoveHoly": 0.0,
        "PerProductMoveHey": 0.0,
        "PerProductMovePem": 0.0,
        "vessel_cap_param": "RToFishVesselCap",
        "vessel_cap": 75,
    },
    "pembroke": {
        "PerProductMovePem": 1.0,
        "PerProductMoveLiv": 0.0,
        "PerProductMoveHoly": 0.0,
        "PerProductMoveHey": 0.0,
        "PerProductMoveFish": 0.0,
        "vessel_cap_param": "RToPemVesselCap",
        "vessel_cap": 122,
    },
    "cherbourg": {
        "vessel_cap_param": "DToCheVesselCap",
        "vessel_cap": 170,
    },
    "rotterdam": {
        "vessel_cap_param": "DToRottVesselCap",
        "vessel_cap": 530,
    },
    "zeebrugge": {
        "vessel_cap_param": "DToZeeVesselCap",
        "vessel_cap": 530,
    },
    "bilbao": {
        "vessel_cap_param": "RToBilVesselCap",
        "vessel_cap": 80,
    },
}

ALL_PORT_SPLIT_PARAMS: Tuple[str, ...] = (
    "PerProductMoveHey",
    "PerProductMoveLiv",
    "PerProductMoveHoly",
    "PerProductMoveFish",
    "PerProductMovePem",
)

# --- Vessel capacity param names (spec §15) -----------------------------------

VESSEL_CAP_MAP: Dict[str, Dict[str, str]] = {
    "dublin": {
        "heysham": "DToHeyVesselCap",
        "liverpool": "DToLivVesselCap",
        "holyhead": "DToHolyVesselCap",
        "cherbourg": "DToCheVesselCap",
        "rotterdam": "DToRottVesselCap",
        "zeebrugge": "DToZeeVesselCap",
    },
    "rosslare": {
        "fishguard": "RToFishVesselCap",
        "pembroke": "RToPemVesselCap",
        "cherbourg": "RToCheVesselCap",
        "bilbao": "RToBilVesselCap",
    },
}

# --- Resources (spec §15) -----------------------------------------------------

RESOURCE_PARAM_MAP: Dict[str, Dict[str, str]] = {
    "dublin": {
        "customs": "NumCustomShedD",
        "dafm": "NumDAFMInspBayD",
        "security": "NumSecurityPostD",
        "tractors": "NumTractorD",
    },
    "rosslare": {
        "customs": "NumCustomShedR",
        "dafm": "NumDAFMInspBayR",
        "security": "NumSecurityPostR",
        "tractors": "NumTractorR",
    },
    "liverpool": {
        "customs": "NumCustomShedLiv",
        "dafm": "NumDAFMInspBayLiv",
        "security": "NumSecurityPostLiv",
        "tractors": "NumTractorLiv",
    },
    "holyhead": {
        "customs": "NumCustomShedHoly",
        "dafm": "NumDAFMInspBayHoly",
        "security": "NumSecurityPostHoly",
        "tractors": "NumTractorHoly",
    },
    "heysham": {
        "customs": "NumCustomShedGB-W",
        "dafm": "NumDAFMInspBayGB-W",
        "security": "NumSecurityPostGB-W",
        "tractors": "NumTractorGB-W",
    },
    "fishguard": {
        "customs": "NumCustomShedGB-W",
        "dafm": "NumDAFMInspBayGB-W",
        "security": "NumSecurityPostGB-W",
        "tractors": "NumTractorGB-W",
    },
    "pembroke": {
        "customs": "NumCustomShedGB-W",
        "dafm": "NumDAFMInspBayGB-W",
        "security": "NumSecurityPostGB-W",
        "tractors": "NumTractorGB-W",
    },
}

# --- Check regime (spec §16) ---------------------------------------------------

CHECK_REGIME_PRESETS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "none": {
        "all_products": {
            "PerGreenTrucksAPImIR": 1.0,
            "DocChkTimeAPImIR": 0,
            "PerPhyChkAPImIR": 0.0,
            "PhyChkTimeAPImIR": 0,
            "PerSecurityChkAPIR": 0.0,
            "SecChkTimeAPImIR": 0,
            "PerCusIntTrucksAPExIR": 0.0,
            "CusIntTimeAPExIR": 0,
            "PerGreenTrucksAPImGB-W": 1.0,
            "DocChkTimeAPImGB-W": 0,
            "PerPhyChkAPImGB-W": 0.0,
            "PhyChkTimeAPImGB-W": 0,
        },
        "agri": {
            "PerGreenTrucksAPImIR": 1.0,
            "DocChkTimeAgriImIR": 0,
            "PerPhyChkAgriImIR": 0.0,
            "PhyChkTimeAgriImIR": 0,
            "PerSecurityChkAgriIR": 0.0,
            "SecChkTimeAgriImIR": 0,
            "PerCusIntTrucksAgriExIR": 0.0,
            "CusIntTimeAgriExIR": 0,
        },
        "category": {
            "PerGreenTrucksAPImIR": 1.0,
            "DocChkTimeCatImIR": 0,
            "PerPhyChkCatImIR": 0.0,
            "PhyChkTimeCatImIR": 0,
            "PerSecurityChkCatIR": 0.0,
            "SecChkTimeCatImIR": 0,
            "PerCusIntTrucksCatExIR": 0.0,
            "CusIntTimeCatExIR": 0,
        },
    },
    "light": {
        "all_products": {
            "PerCusIntTrucksAPExIR": 1.0,
            "CusIntTimeAPExIR": 266,
            "PerGreenTrucksAPImIR": 1.0,
            "PerPhyChkAPImIR": 0.0,
            "DocChkTimeAPImIR": 0,
            "PerSecurityChkAPIR": 0.0,
            "PerCusIntTrucksAPExGB-W": 1.0,
            "CusIntTimeAPExGB-W": 262,
            "PerGreenTrucksAPImGB-W": 1.0,
            "PerPhyChkAPImGB-W": 0.0,
        },
        "agri": {
            "PerCusIntTrucksAgriExIR": 1.0,
            "CusIntTimeAgriExIR": 201,
            "PerGreenTrucksAPImIR": 1.0,
            "PerPhyChkAgriImIR": 0.0,
            "DocChkTimeAgriImIR": 0,
            "PerSecurityChkAgriIR": 0.0,
            "PerCusIntTrucksAgriExGB-W": 1.0,
            "CusIntTimeAgriExGB-W": 246,
        },
        "category": {
            "PerCusIntTrucksCatExIR": 1.0,
            "CusIntTimeCatExIR": 242,
            "PerGreenTrucksAPImIR": 1.0,
            "PerPhyChkCatImIR": 0.0,
            "DocChkTimeCatImIR": 0,
            "PerSecurityChkCatIR": 0.0,
            "PerCusIntTrucksCatExGB-W": 1.0,
            "CusIntTimeCatExGB-W": 201,
        },
    },
    "standard": {
        "all_products": {
            "PerCusIntTrucksAPExIR": 1.0,
            "CusIntTimeAPExIR": 266,
            "PerGreenTrucksAPImIR": 0.9,
            "DocChkTimeAPImIR": 20,
            "PerPhyChkAPImIR": 0.1,
            "PhyChkTimeAPImIR": 60,
            "PerSecurityChkAPIR": 0.05,
            "SecChkTimeAPImIR": 20,
            "PerGreenTrucksAPImGB-W": 0.9,
            "PerPhyChkAPImGB-W": 0.1,
            "PhyChkTimeAPImGB-W": 60,
        },
        "agri": {
            "PerCusIntTrucksAgriExIR": 1.0,
            "CusIntTimeAgriExIR": 201,
            "DocChkTimeAgriImIR": 20,
            "PerPhyChkAgriImIR": 0.1,
            "PhyChkTimeAgriImIR": 60,
            "PerSecurityChkAgriIR": 0.05,
            "SecChkTimeAgriImIR": 20,
        },
        "category": {
            "PerCusIntTrucksCatExIR": 1.0,
            "CusIntTimeCatExIR": 242,
            "DocChkTimeCatImIR": 20,
            "PerPhyChkCatImIR": 0.1,
            "PhyChkTimeCatImIR": 60,
            "PerSecurityChkCatIR": 0.05,
            "SecChkTimeCatImIR": 20,
        },
    },
    "hard": {
        "all_products": {
            "PerCusIntTrucksAPExIR": 1.0,
            "CusIntTimeAPExIR": 266,
            "PerGreenTrucksAPImIR": 0.7,
            "DocChkTimeAPImIR": 242,
            "PerPhyChkAPImIR": 0.3,
            "PhyChkTimeAPImIR": 385,
            "PerSecurityChkAPIR": 0.1,
            "SecChkTimeAPImIR": 377,
            "PerGreenTrucksAPImGB-W": 0.7,
            "PerPhyChkAPImGB-W": 0.3,
            "PhyChkTimeAPImGB-W": 475,
        },
        "agri": {
            "PerCusIntTrucksAgriExIR": 1.0,
            "CusIntTimeAgriExIR": 201,
            "DocChkTimeAgriImIR": 172,
            "PerPhyChkAgriImIR": 0.3,
            "PhyChkTimeAgriImIR": 385,
            "PerSecurityChkAgriIR": 0.1,
            "SecChkTimeAgriImIR": 426,
        },
        "category": {
            "PerCusIntTrucksCatExIR": 1.0,
            "CusIntTimeCatExIR": 242,
            "DocChkTimeCatImIR": 168,
            "PerPhyChkCatImIR": 0.3,
            "PhyChkTimeCatImIR": 398,
            "PerSecurityChkCatIR": 0.1,
            "SecChkTimeCatImIR": 367,
        },
    },
}

PHYCHK_PCT_MAP = {
    "all_products": "PerPhyChkAPImIR",
    "agri": "PerPhyChkAgriImIR",
    "category": "PerPhyChkCatImIR",
}

PHYCHK_TIME_MAP = {
    "all_products": "PhyChkTimeAPImIR",
    "agri": "PhyChkTimeAgriImIR",
    "category": "PhyChkTimeCatImIR",
}

DOCCHK_TIME_MAP = {
    "all_products": "DocChkTimeAPImIR",
    "agri": "DocChkTimeAgriImIR",
    "category": "DocChkTimeCatImIR",
}


def _routing_port(req: ScenarioRequest) -> str:
    """GB port on the active IRE↔GB leg (export: destination; import: origin)."""
    if req.direction == "export":
        return req.destination_port
    return req.origin_port


def _irish_port(req: ScenarioRequest) -> str:
    """Irish terminal for resource parameters (v1 freeze)."""
    if req.direction == "export":
        return req.origin_port
    return req.destination_port


def _vessel_cap_param_name(req: ScenarioRequest) -> str:
    """Resolve vessel-cap column for the IRE↔GB leg (symmetric in both directions)."""
    if req.direction == "export":
        return VESSEL_CAP_MAP[req.origin_port][req.destination_port]
    return VESSEL_CAP_MAP[req.destination_port][req.origin_port]


def translate(req: ScenarioRequest, medians: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a dict with all 153 raw parameter names.

    Starts from ``medians``, then applies the eight spec §15 steps.
    """
    params: Dict[str, Any] = dict(medians)

    # Step 1 — zero all corridor volumes
    for k in list(params.keys()):
        if k.startswith("Vol"):
            params[k] = 0.0

    # Step 2 — active Vol*
    vol_key = VOLUME_MAP[(req.commodity_type, req.direction, req.route_type)]
    params[vol_key] = float(req.product_volume_tonnes)

    # Step 3 — port routing splits (GB leg)
    rp = _routing_port(req)
    port_defaults = PORT_ROUTING[rp]
    for k, v in port_defaults.items():
        if k in _INTERNAL_PORT_ROUTING_KEYS:
            continue
        params[k] = v
    for port_param in ALL_PORT_SPLIT_PARAMS:
        if port_param not in port_defaults:
            params[port_param] = 0.0

    # Step 4 — vessel capacity on the active cap column
    vessel_cap_key = _vessel_cap_param_name(req)
    cap_default = port_defaults["vessel_cap"]
    params[vessel_cap_key] = float(
        req.vessel_capacity_trailers
        if req.vessel_capacity_trailers is not None
        else cap_default
    )

    # Step 5 — check regime + optional overrides
    regime_params = CHECK_REGIME_PRESETS[req.check_regime][req.commodity_type]
    params.update(regime_params)
    if req.physical_check_pct is not None:
        params[PHYCHK_PCT_MAP[req.commodity_type]] = req.physical_check_pct
    if req.physical_check_time_mins is not None:
        params[PHYCHK_TIME_MAP[req.commodity_type]] = float(req.physical_check_time_mins)
    if req.doc_check_time_mins is not None:
        params[DOCCHK_TIME_MAP[req.commodity_type]] = float(req.doc_check_time_mins)

    # Step 6 — resources on Irish port
    resource_map = RESOURCE_PARAM_MAP[_irish_port(req)]
    if req.customs_officers:
        params[resource_map["customs"]] = req.customs_officers
    if req.dafm_officers:
        params[resource_map["dafm"]] = req.dafm_officers
    if req.security_officers:
        params[resource_map["security"]] = req.security_officers
    if req.tractors:
        params[resource_map["tractors"]] = req.tractors

    # Step 7 — shelf life & truck mix
    params["AvgShelflife(ProdCat)"] = float(req.shelf_life_days or 14.0)
    params["UnAccTrucks(%)"] = float(req.unaccompanied_pct if req.unaccompanied_pct is not None else 0.5)

    # Step 8 — check costs
    params["DocCheckCost"] = float(req.doc_check_cost_eur if req.doc_check_cost_eur is not None else 50.0)
    params["PhyCheckCost"] = float(req.phy_check_cost_eur if req.phy_check_cost_eur is not None else 500.0)
    params["SecurityCheckCost"] = float(req.sec_check_cost_eur if req.sec_check_cost_eur is not None else 500.0)

    return params


def baseline_medians_for_tests() -> Dict[str, float]:
    """153 training inputs at 1.0 — for unit tests only."""
    return {k: 1.0 for k in TRAINING_COLUMN_ORDER}
