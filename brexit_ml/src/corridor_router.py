"""
Infer active trade corridor from non-zero ``Vol*`` inputs (spec §2, §4.2).

After ``param_translator.translate``, exactly one ``Vol*`` is usually non-zero; raw
``POST /predict`` bodies may still be inspected the same way for logging or validation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Set, Tuple

# Corridor id → Vol* columns that activate that corridor (disjoint groups).
_VOL_GROUPS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "ire_gb_direct",
        (
            "VolAllPImGB",
            "VolAllPExGB",
            "VolAgriImGB",
            "VolAgriExGB",
            "VolCatImGB",
            "VolCatExGB",
        ),
    ),
    (
        "eu_landbridge",
        (
            "VolAllPImEULB",
            "VolAllPExEULB",
            "VolAgriImEULB",
            "VolAgriExEULB",
            "VolCatImEULB",
            "VolCatExEULB",
        ),
    ),
    (
        "eu_cherbourg",
        (
            "VolAllPImViaChe",
            "VolAllPExViaChe",
            "VolAgriImViaChe",
            "VolAgriExViaChe",
            "VolCatImViaChe",
            "VolCatExViaChe",
        ),
    ),
    (
        "eu_rotterdam",
        (
            "VolAllPImViaRott",
            "VolAllPExViaRott",
            "VolAgriImViaRott",
            "VolAgriExViaRott",
            "VolCatImViaRott",
            "VolCatExViaRott",
        ),
    ),
    (
        "eu_zeebrugge",
        (
            "VolAllPImViaZee",
            "VolAllPExViaZee",
            "VolAgriImViaZee",
            "VolAgriExViaZee",
            "VolCatImViaZee",
            "VolCatExViaZee",
        ),
    ),
    (
        "eu_bilbao",
        (
            "VolAllPImViaBil",
            "VolCatExViaBil",
        ),
    ),
    (
        "gb_eu_dover_calais",
        (
            "VolAllPImGBEU",
            "VolAllPExGBEU",
        ),
    ),
)

_VOL_KEY_TO_CORRIDOR: Dict[str, str] = {}
for cid, keys in _VOL_GROUPS:
    for k in keys:
        _VOL_KEY_TO_CORRIDOR[k] = cid


def corridor_for_vol_key(vol_key: str) -> str:
    """Map a single ``Vol*`` column name to a corridor id, or ``unknown_vol``."""
    return _VOL_KEY_TO_CORRIDOR.get(vol_key, "unknown_vol")


def active_corridor_from_inputs(inputs: Mapping[str, Any], *, eps: float = 1e-9) -> str:
    """
    Return the active corridor id from non-zero ``Vol*`` entries.

    - ``none``: all ``Vol*`` are ~zero (or absent).
    - ``mixed_corridors``: non-zero volumes span more than one corridor group.
    - ``unknown_vol``: a non-zero ``Vol*`` name is not in the routing table (e.g. dropped column).
    """
    active_keys: List[str] = []
    for k, v in inputs.items():
        if not k.startswith("Vol"):
            continue
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if abs(fv) > eps:
            active_keys.append(k)

    if not active_keys:
        return "none"

    labels: Set[str] = set()
    for k in active_keys:
        labels.add(corridor_for_vol_key(k))

    if "unknown_vol" in labels:
        return "unknown_vol"
    if len(labels) > 1:
        return "mixed_corridors"
    return next(iter(labels))


def nonzero_vol_keys(inputs: Mapping[str, Any], *, eps: float = 1e-9) -> List[str]:
    """Return ``Vol*`` keys with magnitude above ``eps`` (stable sort by key)."""
    out: List[str] = []
    for k in sorted(inputs.keys()):
        if not k.startswith("Vol"):
            continue
        try:
            fv = float(inputs[k])
        except (TypeError, ValueError):
            continue
        if abs(fv) > eps:
            out.append(k)
    return out
