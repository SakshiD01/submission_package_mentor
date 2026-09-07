"""
Pydantic models for semantic API and errors.

See docs/ml/spec/brexit_ml_engine_spec.md §13–14, §22.
`origin_port` / `destination_port` use the full port union so Section 19 examples validate
(the spec snippet only listed Irish ports for `origin_port`; VALID_OPTIONS §13 includes all legs).
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# --- Shared literals (spec §13) ------------------------------------------------

SupplierRegion = Literal["ireland", "great_britain", "eu"]
# Spec §13 lists only GB/EU; Section 19 example uses "ireland" when the destination is Irish ports.
DestinationRegion = Literal["ireland", "great_britain", "eu"]

# All ports that may appear as origin or destination (§13 VALID_OPTIONS).
PortCode = Literal[
    "dublin",
    "rosslare",
    "liverpool",
    "holyhead",
    "heysham",
    "fishguard",
    "pembroke",
    "cherbourg",
    "rotterdam",
    "zeebrugge",
    "bilbao",
]

CommodityType = Literal["all_products", "agri", "category"]
Direction = Literal["export", "import"]

RouteType = Literal[
    "direct_gb",
    "landbridge",
    "direct_cherbourg",
    "direct_rotterdam",
    "direct_zeebrugge",
    "direct_bilbao",
]

CheckRegime = Literal["none", "light", "standard", "hard"]

PredictionStatus = Literal["ok", "low_coverage", "zero_predicted", "not_trained"]
Phase = Literal[1, 2]
OverallConfidence = Literal["high", "medium", "low"]


class ScenarioRequest(BaseModel):
    """Seven semantic dimensions → param translator (spec §13)."""

    supplier_region: SupplierRegion
    origin_port: PortCode
    destination_region: DestinationRegion
    destination_port: PortCode
    commodity_type: CommodityType
    direction: Direction

    product_volume_tonnes: float = Field(..., gt=0, description="Single user-provided volume (tonnes).")

    route_type: RouteType
    vessel_capacity_trailers: Optional[int] = Field(
        None,
        ge=1,
        description="If None, filled from port defaults / registry.",
    )

    check_regime: CheckRegime
    physical_check_pct: Optional[float] = Field(None, ge=0.0, le=1.0)
    physical_check_time_mins: Optional[int] = Field(None, ge=0)
    doc_check_time_mins: Optional[int] = Field(None, ge=0)
    security_check_pct: Optional[float] = Field(None, ge=0.0, le=1.0)
    security_check_time_mins: Optional[int] = Field(None, ge=0)

    customs_officers: Optional[int] = Field(None, ge=0)
    dafm_officers: Optional[int] = Field(None, ge=0)
    security_officers: Optional[int] = Field(None, ge=0)
    tractors: Optional[int] = Field(None, ge=0)

    shelf_life_days: Optional[float] = Field(None, gt=0)
    unaccompanied_pct: Optional[float] = Field(None, ge=0.0, le=1.0)
    doc_check_cost_eur: Optional[float] = Field(None, ge=0)
    phy_check_cost_eur: Optional[float] = Field(None, ge=0)
    sec_check_cost_eur: Optional[float] = Field(None, ge=0)


class PredictionResult(BaseModel):
    """Single KPI prediction (spec §14)."""

    value: Optional[float] = None
    unit: str
    status: PredictionStatus
    phase: Phase
    coverage_pct: int = Field(..., ge=0, le=100)
    r2: Optional[float] = None


# Group label → output name → fields (spec §14 example).
ScenarioResults = Dict[str, Dict[str, Any]]


class ScenarioResponse(BaseModel):
    """Semantic prediction response (spec §14)."""

    scenario_id: str
    corridor: str
    commodity: str
    direction: str
    check_regime: str
    model_version: str

    results: ScenarioResults

    warnings: List[str]
    overall_confidence: OverallConfidence


class ErrorResponse(BaseModel):
    """JSON error body (spec §22)."""

    error: str
    detail: str


# --- UI / wizard helpers (spec §13) --------------------------------------------

VALID_OPTIONS: Dict[str, Any] = {
    "supplier_region": ["ireland", "great_britain", "eu"],
    "origin_port": {
        "ireland": ["dublin", "rosslare"],
        "great_britain": ["liverpool", "holyhead", "heysham", "fishguard", "pembroke"],
        "eu": ["cherbourg", "rotterdam", "zeebrugge", "bilbao"],
    },
    "destination_region": ["ireland", "great_britain", "eu"],
    "destination_port": {
        "ireland": ["dublin", "rosslare"],
        "great_britain": ["liverpool", "holyhead", "heysham", "fishguard", "pembroke"],
        "eu": ["cherbourg", "rotterdam", "zeebrugge", "bilbao"],
    },
    "commodity_type": ["all_products", "agri", "category"],
    "direction": ["export", "import"],
    "route_type": {
        "great_britain": ["direct_gb"],
        "eu": ["landbridge", "direct_cherbourg", "direct_rotterdam", "direct_zeebrugge", "direct_bilbao"],
    },
    "check_regime": ["none", "light", "standard", "hard"],
}
