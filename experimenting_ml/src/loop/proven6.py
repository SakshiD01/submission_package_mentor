"""
PROVEN_6 (spec.md §7 item 13, 29-Aug): 6 KPIs with an empirically justified,
benchmarked UQ method choice, built alongside DEMO_4, not replacing it.

DEMO_4 (kpi_scope.py) was chosen to cover the 3 GENERIC DISPATCH PATHS
(bagged-tree / GPR / conformal). PROVEN_6 is chosen for a different reason:
the mentor asked to benchmark several candidate UQ methods per SPECIFIC
MODEL FAMILY (GPR-Matern, ExtraTrees, ElasticNet, Lasso, SVR, GradientBoosting)
and fix one method per family with evidence (UQ_Method_Benchmark.xlsx). Kept
as a separate module rather than folded into dispatch.py's registry-driven
routing, because the winning method here isn't a clean per-family rule the
way the 3 main dispatch paths are:

    KPI               Family              Winning method            vs. dispatch.py's own default
    ---               ------              --------------            ------------------------------
    wt_ob_lb          GPR (Matern)        Conformalized GPR         OVERRIDE (default would be native GPR)
    tt_ob_lb          ExtraTrees          Native ensemble SD        matches default
    uti_cus_r         ElasticNet          CV+ (mapie)                OVERRIDE (default would be split conformal)
    wt_ob_a_gb_dub    Lasso               Split conformal            matches default
    wt_ib_na_ross     SVR (RBF)           Split conformal            matches default
    tt_ib_lb          GradientBoosting    CV+ (mapie)                OVERRIDE, AND a different model family
                                                                      than the KPI's real registered winner --
                                                                      see the caveat below.

Caveat on tt_ib_lb, stated plainly, not hidden: this KPI's actual registered
production winner is "stacking" (a 5-model blend), not "gradient_boosting" --
gradient_boosting is only one of that stack's 5 base learners. tt_ib_lb was
picked for the GradientBoosting benchmark on 29-Aug because GradientBoosting
has NO KPI anywhere in the registry where it's the outright winner. This
means get_proven_uq_estimator("tt_ib_lb") gives a standalone GradientBoosting
model's uncertainty, which is NOT what production actually predicts for
this KPI -- fine for the benchmarking/proof exercise the mentor asked for,
but NOT a drop-in replacement for tt_ib_lb's real dispatch path if this is
ever used for live predictions rather than the UQ-method comparison itself.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .uq.dispatch import load_registry

PROVEN_6: List[str] = [
    "wt_ob_lb",
    "tt_ob_lb",
    "uti_cus_r",
    "wt_ob_a_gb_dub",
    "wt_ib_na_ross",
    "tt_ib_lb",
]

# kpi_slug -> which UQEstimator mechanism won its family's benchmark
PROVEN_METHOD: Dict[str, str] = {
    "wt_ob_lb": "conformal_fallback",
    "tt_ob_lb": "bagged_tree_native",
    "uti_cus_r": "mapie_cv_plus",
    "wt_ob_a_gb_dub": "conformal_fallback",
    "wt_ib_na_ross": "conformal_fallback",
    "tt_ib_lb": "mapie_cv_plus",
}

# Only needed where the benchmarked family differs from registry.json's own
# registered_as (currently just tt_ib_lb -- see the module docstring's caveat).
PROVEN_REGISTERED_AS_OVERRIDE: Dict[str, str] = {
    "tt_ib_lb": "gradient_boosting",
}


def get_proven_uq_estimator(kpi_slug: str, registry: Optional[Dict[str, Any]] = None):
    """PROVEN_6's per-slug UQEstimator, using each family's benchmarked
    winning method -- NOT dispatch.get_uq_estimator()'s generic registry
    routing, since the winning method differs from that default for half
    of PROVEN_6 (see module docstring's table)."""
    if kpi_slug not in PROVEN_6:
        raise KeyError(f"{kpi_slug!r} is not in PROVEN_6: {PROVEN_6}")

    reg = registry if registry is not None else load_registry()
    if kpi_slug not in reg.get("outputs", {}):
        raise KeyError(f"{kpi_slug!r} not in registry outputs")

    registered_as = PROVEN_REGISTERED_AS_OVERRIDE.get(
        kpi_slug, reg["outputs"][kpi_slug]["registered_as"]
    )
    method = PROVEN_METHOD[kpi_slug]

    if method == "bagged_tree_native":
        from .uq.tree_native import BaggedTreeJackknife

        return BaggedTreeJackknife(kpi_slug=kpi_slug, registered_as=registered_as)
    if method == "conformal_fallback":
        from .uq.conformal_fallback import ConformalFallback

        return ConformalFallback(kpi_slug=kpi_slug, registered_as=registered_as)
    if method == "mapie_cv_plus":
        from .uq.mapie_cv_plus import MapieCVPlus

        return MapieCVPlus(kpi_slug=kpi_slug, registered_as=registered_as)

    raise ValueError(f"unknown method {method!r} for {kpi_slug!r}")  # pragma: no cover -- defensive
