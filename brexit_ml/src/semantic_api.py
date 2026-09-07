"""
Semantic FastAPI routes (spec §12–14): /scenario/predict, validate, options, schema.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from corridor_router import active_corridor_from_inputs
from ml_engine import MLEngine
from output_filter import outputs_for_scenario
from param_translator import translate
from phase1_scenarios import validate_phase1_scenario
from schemas import ScenarioRequest, ScenarioResponse, VALID_OPTIONS


def _col_to_slug(name: str) -> str:
    """Match ``train.col_to_slug`` / registry keys without importing ``train`` (heavy deps)."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug[:80]


def _scenario_ports(req: ScenarioRequest) -> Tuple[str, str]:
    """(irish_port, gb_port) for Phase 1 IRE↔GB."""
    if req.direction == "export":
        return req.origin_port, req.destination_port
    return req.destination_port, req.origin_port


def _corridor_label(req: ScenarioRequest) -> str:
    sr = req.supplier_region.replace("_", " ").title()
    dr = req.destination_region.replace("_", " ").title()
    return f"{sr} → {dr} ({req.origin_port} → {req.destination_port})"


def _scenario_id(req: ScenarioRequest) -> str:
    payload = "|".join(
        [
            req.supplier_region,
            req.origin_port,
            req.destination_region,
            req.destination_port,
            req.commodity_type,
            req.direction,
            f"{req.product_volume_tonnes:.6g}",
            req.route_type,
            req.check_regime,
        ]
    )
    return "sc_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _group_bucket(display_name: str) -> str:
    ln = display_name.lower()
    if ln.startswith("transportation time"):
        return "transit"
    if "shelflife" in ln or "shelf life" in ln:
        return "shelf_life"
    if "queue" in ln:
        return "vessel_queues"
    if "cost" in ln:
        return "costs"
    if "utilisation" in ln:
        return "resource_utilisation"
    return "border_delay"


def _group_results(
    display_names: List[str],
    preds: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Nest slug-keyed PredictionResult dicts under §14 groups (display names as inner keys)."""
    grouped: Dict[str, Dict[str, Any]] = {}
    for name in display_names:
        slug = _col_to_slug(name)
        if slug not in preds:
            continue
        pr = preds[slug]
        bucket = _group_bucket(name)
        grouped.setdefault(bucket, {})
        grouped[bucket][name] = pr.model_dump()
    return grouped


def _overall_confidence(results_by_group: Dict[str, Dict[str, Any]]) -> str:
    statuses: List[str] = []
    for grp in results_by_group.values():
        for pr in grp.values():
            if isinstance(pr, dict) and "status" in pr:
                statuses.append(pr["status"])
    if not statuses:
        return "medium"
    if all(s == "ok" for s in statuses):
        return "high"
    n = len(statuses)
    bad = sum(1 for s in statuses if s in ("low_coverage", "zero_predicted"))
    if bad > n / 2:
        return "low"
    if any(s == "low_coverage" for s in statuses):
        return "medium"
    if any(s == "zero_predicted" for s in statuses):
        return "medium"
    return "medium"


WIZARD_STEPS: List[Dict[str, Any]] = [
    {
        "step": 1,
        "title": "Journey",
        "description": "Supplier region, ports, and trade direction (spec §12.3).",
        "fields": [
            "supplier_region",
            "origin_port",
            "destination_region",
            "destination_port",
            "direction",
        ],
    },
    {
        "step": 2,
        "title": "Commodity & volume",
        "fields": ["commodity_type", "product_volume_tonnes"],
    },
    {
        "step": 3,
        "title": "Route",
        "fields": ["route_type", "vessel_capacity_trailers"],
    },
    {
        "step": 4,
        "title": "Checks",
        "fields": [
            "check_regime",
            "physical_check_pct",
            "physical_check_time_mins",
            "doc_check_time_mins",
            "security_check_pct",
            "security_check_time_mins",
        ],
    },
    {
        "step": 5,
        "title": "Resources",
        "fields": ["customs_officers", "dafm_officers", "security_officers", "tractors"],
    },
    {
        "step": 6,
        "title": "Product & costs",
        "fields": [
            "shelf_life_days",
            "unaccompanied_pct",
            "doc_check_cost_eur",
            "phy_check_cost_eur",
            "sec_check_cost_eur",
        ],
    },
]


def _http_400_from_phase1(exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=400, content=exc.detail)
    return JSONResponse(
        status_code=400,
        content={"error": "invalid_input", "detail": str(exc.detail)},
    )


def register_semantic_routes(app: FastAPI) -> None:
    """Attach ``/scenario/*`` routes to an app created by ``ml_api.create_app`` (expects ``app.state.get_engine``)."""
    router = APIRouter()

    @router.get("/options")
    def scenario_options() -> Any:
        return VALID_OPTIONS

    @router.get("/schema")
    def scenario_schema() -> Any:
        return {
            "wizard_steps": WIZARD_STEPS,
            "scenario_request_schema": ScenarioRequest.model_json_schema(),
        }

    @router.post("/validate")
    def scenario_validate(body: Dict[str, Any], request: Request) -> Any:
        try:
            req = ScenarioRequest.model_validate(body)
        except ValidationError as e:
            return JSONResponse(
                status_code=400,
                content={"valid": False, "errors": e.errors()},
            )
        try:
            validate_phase1_scenario(req)
        except HTTPException as exc:
            if exc.status_code == 400:
                msg = (
                    exc.detail.get("detail")
                    if isinstance(exc.detail, dict)
                    else str(exc.detail)
                )
                return JSONResponse(
                    status_code=400,
                    content={"valid": False, "errors": [msg]},
                )
            raise

        get_engine = request.app.state.get_engine  # type: ignore[attr-defined]
        eng: Optional[MLEngine] = get_engine()
        if eng is not None:
            raw = translate(req, eng.registry["training_medians"])
            ac = active_corridor_from_inputs(raw)
        else:
            ac = "ire_gb_direct" if req.route_type == "direct_gb" else "eu_phase2"

        ac_label = "IRE_GB" if ac == "ire_gb_direct" else ac.upper()

        return {"valid": True, "warnings": [], "active_corridor": ac_label}

    @router.post("/predict")
    def scenario_predict(req: ScenarioRequest, request: Request) -> Any:
        get_engine = request.app.state.get_engine  # type: ignore[attr-defined]
        eng: Optional[MLEngine] = get_engine()
        if eng is None:
            mv = getattr(request.app.state, "model_version", "v1")  # type: ignore[attr-defined]
            return JSONResponse(
                status_code=503,
                content={
                    "error": "model_not_ready",
                    "detail": f"No model files found in models/{mv}/. Run: python src/train.py",
                },
            )

        try:
            validate_phase1_scenario(req)
        except HTTPException as exc:
            if exc.status_code == 400:
                return _http_400_from_phase1(exc)
            raise

        medians = eng.registry["training_medians"]
        raw = translate(req, medians)
        preds = eng.predict(raw)

        irish, gb = _scenario_ports(req)
        display_names = outputs_for_scenario(
            req.commodity_type,
            req.direction,
            req.route_type,
            irish,
            gb,
        )
        grouped = _group_results(display_names, preds)
        conf = _overall_confidence(grouped)

        return ScenarioResponse(
            scenario_id=_scenario_id(req),
            corridor=_corridor_label(req),
            commodity=req.commodity_type,
            direction=req.direction,
            check_regime=req.check_regime,
            model_version=eng.model_version,
            results=grouped,
            warnings=[],
            overall_confidence=conf,
        ).model_dump()

    app.include_router(router, prefix="/scenario", tags=["scenario"])
