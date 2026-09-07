"""
Phase 1 (IRE ↔ GB East/West) scenario allow-list (spec §19).

Unsupported combinations must be rejected before translation — callers typically map
`HTTPException` to `{"error": "invalid_input", "detail": ...}` (spec §22).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST

if TYPE_CHECKING:
    from schemas import ScenarioRequest

# Spec §19 "Supported journeys" — Ireland origin ports paired with GB destination ports (export leg).
_PHASE1_EXPORT_EDGES: frozenset[tuple[str, str]] = frozenset(
    {
        ("dublin", "liverpool"),
        ("dublin", "holyhead"),
        ("dublin", "heysham"),
        ("rosslare", "fishguard"),
        ("rosslare", "pembroke"),
    }
)

# Import leg: same physical pairs with GB as origin and Ireland as destination (§19 example).
_PHASE1_IMPORT_EDGES: frozenset[tuple[str, str]] = frozenset(
    (dst, src) for src, dst in _PHASE1_EXPORT_EDGES
)


def _reject(msg: str) -> None:
    raise HTTPException(
        status_code=HTTP_400_BAD_REQUEST,
        detail={"error": "invalid_input", "detail": msg},
    )


def validate_phase1_scenario(req: "ScenarioRequest") -> None:
    """
    Raise HTTP 400 if the scenario is outside Phase 1 (spec §19).

    Rules:
    - `route_type` must be `direct_gb`.
    - `supplier_region` / `destination_region` must be `ireland` and `great_britain` only (no EU).
    - `direction` must align with regions and with the §19 port pairs.
    """
    if req.route_type != "direct_gb":
        _reject(
            "Unsupported Phase 1 scenario: route_type must be 'direct_gb' for the IRE↔GB corridor."
        )

    if req.supplier_region == "eu" or req.destination_region == "eu":
        _reject(
            "Unsupported Phase 1 scenario: EU legs are not enabled; use IRE↔Great Britain only."
        )

    od = (req.origin_port, req.destination_port)

    if req.direction == "export":
        if req.supplier_region != "ireland" or req.destination_region != "great_britain":
            _reject(
                "Unsupported Phase 1 scenario: export journeys require supplier_region='ireland' "
                "and destination_region='great_britain'."
            )
        if od not in _PHASE1_EXPORT_EDGES:
            _reject(
                "Unsupported Phase 1 scenario: origin/destination ports must match a §19 "
                f"Dublin→GB-West or Rosslare→GB-West pair; got {req.origin_port!r} → {req.destination_port!r}."
            )
        return

    if req.direction == "import":
        if req.supplier_region != "great_britain" or req.destination_region != "ireland":
            _reject(
                "Unsupported Phase 1 scenario: import journeys require supplier_region='great_britain' "
                "and destination_region='ireland'."
            )
        if od not in _PHASE1_IMPORT_EDGES:
            _reject(
                "Unsupported Phase 1 scenario: origin/destination ports must match a §19 "
                f"GB-West→Dublin or GB-West→Rosslare pair; got {req.origin_port!r} → {req.destination_port!r}."
            )
        return

    _reject(f"Unsupported Phase 1 scenario: invalid direction {req.direction!r}.")
