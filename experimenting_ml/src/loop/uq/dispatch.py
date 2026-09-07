"""
T2.1: generic, registry-driven UQ dispatcher (spec.md §5.1, §5.1.1 tier 1).

Never hardcode a KPI list. Every function here takes "any KPI" and routes it
to one of three paths by reading nolhc_ml's model registry -- the same
mechanism spec.md §5.1.1 uses to justify "all 20 is not 20 separate builds":

    bagged-tree native  (RandomForest, ExtraTrees)      -- 3 of 20 KPIs, T2.3 new code
    GPR native           (GPR_RBF, GPR_Matern)           -- 4 of 20 KPIs, T2.3 reuses evaluate.py
    conformal fallback   (everything else, incl. stacking) -- 13 of 20 KPIs, already built

Unknown/unrecognised model names fall back to conformal rather than raising --
conformal is the safe, model-agnostic default and is correct for any family
not explicitly in the native buckets (spec.md §5.1's dispatch table).
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# nolhc_ml/models/v1/registry.json relative to this file:
#   uq -> loop -> src -> experimenting_ml -> <repo root> -> nolhc_ml/models/v1/registry.json
_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_REGISTRY_PATH = _REPO_ROOT / "nolhc_ml" / "models" / "v1" / "registry.json"

BAGGED_TREE_MODELS = frozenset({"random_forest", "extra_trees"})
GPR_MODELS = frozenset({"gpr_rbf", "gpr_matern"})


class DispatchPath(str, Enum):
    BAGGED_TREE_NATIVE = "bagged_tree_native"
    GPR_NATIVE = "gpr_native"
    CONFORMAL_FALLBACK = "conformal_fallback"


def load_registry(path: Optional[Path] = None) -> Dict[str, Any]:
    reg_path = Path(path) if path is not None else DEFAULT_REGISTRY_PATH
    if not reg_path.is_file():
        raise FileNotFoundError(
            f"Missing registry: {reg_path}. Run nolhc_ml/src/train.py first, "
            "or pass an explicit path=... for tests."
        )
    with open(reg_path, encoding="utf-8") as f:
        return json.load(f)


def classify_kpi(registered_as: str) -> DispatchPath:
    """Pure function: a model-family name -> which UQ path handles it.

    This is the whole reason T2.1's dispatcher doesn't need to know about
    KPIs at all, just about what nolhc_ml's train.py already registered.
    """
    name = (registered_as or "").strip().lower()
    if name in BAGGED_TREE_MODELS:
        return DispatchPath.BAGGED_TREE_NATIVE
    if name in GPR_MODELS:
        return DispatchPath.GPR_NATIVE
    return DispatchPath.CONFORMAL_FALLBACK


def kpis_by_path(registry: Optional[Dict[str, Any]] = None) -> Dict[DispatchPath, List[str]]:
    """All KPI slugs in the registry, grouped by dispatch path.

    Used both for the demo-4/stretch-20 split (spec.md §5.1.1) and as a sanity
    check that the 3/4/13 breakdown quoted in the spec still holds if the
    registry is retrained and winners change.
    """
    reg = registry if registry is not None else load_registry()
    buckets: Dict[DispatchPath, List[str]] = {p: [] for p in DispatchPath}
    for slug, info in reg.get("outputs", {}).items():
        path = classify_kpi(info.get("registered_as", ""))
        buckets[path].append(slug)
    return buckets


def get_uq_estimator(kpi_slug: str, registry: Optional[Dict[str, Any]] = None):
    """Factory: KPI slug -> the right UQEstimator instance, uninstantiated on model params.

    Estimator bodies are stubs until T2.3 (26-27 Aug); this factory and the
    routing above are the real, tested T2.1 deliverable -- see
    experimenting_ml/tests/test_loop_dispatch.py.
    """
    reg = registry if registry is not None else load_registry()
    outputs = reg.get("outputs", {})
    if kpi_slug not in outputs:
        raise KeyError(f"{kpi_slug!r} not in registry outputs: {sorted(outputs)[:5]}...")

    kpi_info = outputs[kpi_slug]
    registered_as = kpi_info.get("registered_as", "")
    path = classify_kpi(registered_as)

    # Local imports: avoids importing sklearn/joblib-heavy modules for callers
    # that only want the routing decision (e.g. kpis_by_path() in a unit test).
    if path is DispatchPath.BAGGED_TREE_NATIVE:
        from .tree_native import BaggedTreeJackknife

        return BaggedTreeJackknife(kpi_slug=kpi_slug, registered_as=registered_as)
    if path is DispatchPath.GPR_NATIVE:
        from .gpr_native import GPRNative

        return GPRNative(kpi_slug=kpi_slug, registered_as=registered_as)

    from .conformal_fallback import ConformalFallback

    # "stacking" is itself a conformal-fallback winner (spec.md §5.1) and
    # needs its base learner names to be rebuildable via nolhc_ml's
    # _rebuild_estimator() -- without this, every stacking KPI would raise
    # at fit() time despite routing "correctly" (caught by real-data smoke
    # test T2.3, 26-Aug: tt_ib_dr crashed here before this line existed).
    base_learners = kpi_info.get("stack_base_learners") or []
    return ConformalFallback(
        kpi_slug=kpi_slug, registered_as=registered_as, base_learners=base_learners
    )
