"""
Two-tier KPI scope (spec.md §5.1.1): generic-by-default, demo-4, stretch-20.

DEMO_4 is the core, validated-in-depth scope the 10-Sep report leans on --
one KPI per dispatch path, plus a known-bad stress test. ALL_20 is derived
generically from the registry (never hand-maintained) and is only run
opportunistically in the BUFFER slot (1-Sep) if T2.1-T2.8 haven't slipped;
it is explicitly not required for v0 sign-off (spec.md §5.5).
"""

from __future__ import annotations

from typing import List, Optional

from .uq.dispatch import DEFAULT_REGISTRY_PATH, load_registry

# spec.md §5.1's KPI table -- one per dispatch path, plus TT_IB_DR as the
# known-bad (R2=-0.12) stress test on the conformal-fallback path.
DEMO_4: List[str] = [
    "tt_ob_agri",       # ExtraTrees, R2=0.90  -- bagged-tree native
    "uti_dafm_r",       # GPR_RBF,   R2=0.95  -- GPR native
    "wt_ob_a_gb_ross",  # CatBoost,  R2=0.85  -- conformal fallback, boosting family
    "tt_ib_dr",         # Stacking,  R2=-0.12 -- conformal fallback, stress test
]


def all_kpi_slugs(registry_path=DEFAULT_REGISTRY_PATH) -> List[str]:
    """Stretch-20 scope (spec.md §5.1.1 tier 3): every KPI currently registered.

    Generic by construction -- reads whatever nolhc_ml/train.py last
    registered, so this does not need updating if the registry is retrained
    and winners change.
    """
    registry = load_registry(registry_path)
    return sorted(registry.get("outputs", {}).keys())


def resolve_scope(name: str, registry_path: Optional[str] = None) -> List[str]:
    """"demo4" | "all20" | "all" -> list of KPI slugs. The one place a caller
    (a CLI flag, a test) picks which tier to run, per spec.md §5.1.1."""
    key = name.strip().lower()
    if key in ("demo4", "demo", "core"):
        return list(DEMO_4)
    if key in ("all20", "all", "stretch", "stretch20"):
        return all_kpi_slugs(registry_path or DEFAULT_REGISTRY_PATH)
    raise ValueError(f"Unknown KPI scope {name!r}; expected 'demo4' or 'all20'")
