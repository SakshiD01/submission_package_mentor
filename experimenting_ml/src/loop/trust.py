"""
trust_score(): the one criterion, shared across both cases (spec.md §1, §5.1),
now shaped per the mentor's threshold guidance (spec.md §7 item 3, resolved
25-Aug-2026): calibrate per KPI as the working default; flag a candidate if
ANY KPI falls below its own threshold; include a global-threshold comparison
in the experimental evaluation without blocking implementation.

Shape, and why it isn't two equal scalars:
    - the UQ term is per KPI (each KPI has its own UQEstimator, §5.1's three
      dispatch paths) -- 20 separate normalized interval widths per candidate
    - the novelty term is per CANDIDATE POINT only -- novelty is about where
      the 35-dim input sits, not which KPI you're about to predict, so the
      same novelty_term is reused across every KPI for a given candidate

Naming note: "trust_score" is kept for continuity with spec.md, but the
value returned is a *risk* score -- non-negative, higher means LESS
trustworthy (it's uq_width + novelty, both >= 0). Flagging is
"trust_score(...) > threshold", which implements the mentor's "flag if
[confidence] falls below its threshold" on an equivalent, non-inverted scale.
This is documented once, here, so nobody has to re-derive the sign convention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np


def trust_score(uq_normalized_width: float, novelty_term: float) -> float:
    """v0 combination (spec.md §5.1): sum. Weighting is an explicit open
    question (spec.md §7 item 3) left for T2.6/T2.8 experimentation, not
    resolved here -- sum is the documented starting point, not a final claim."""
    if uq_normalized_width < 0 or novelty_term < 0:
        raise ValueError(
            f"expected non-negative terms, got uq={uq_normalized_width}, novelty={novelty_term}"
        )
    return uq_normalized_width + novelty_term


def calibrate_thresholds_per_kpi(
    calibration_scores: Dict[str, np.ndarray], quantile: float = 0.9
) -> Dict[str, float]:
    """Per-KPI calibration (mentor's working default, spec.md §7 item 3):
    each KPI's threshold is its own `quantile` of trust_score over a
    calibration set (e.g. CV out-of-fold points) -- correct for KPIs that
    differ wildly in scale and noise (wait-time hours vs. utilisation
    fractions), unlike a single pooled threshold.
    """
    if not 0.0 < quantile < 1.0:
        raise ValueError(f"quantile must be in (0, 1), got {quantile}")
    return {kpi: float(np.quantile(scores, quantile)) for kpi, scores in calibration_scores.items()}


def calibrate_threshold_global(
    calibration_scores: Dict[str, np.ndarray], quantile: float = 0.9
) -> float:
    """Global-threshold variant. Not the working default -- exists so Task 2's
    experimental evaluation can run both and compare, per the mentor's
    explicit ask (spec.md §7 item 3), without blocking implementation on
    per-KPI."""
    if not 0.0 < quantile < 1.0:
        raise ValueError(f"quantile must be in (0, 1), got {quantile}")
    if not calibration_scores:
        raise ValueError("calibration_scores is empty")
    pooled = np.concatenate([np.asarray(v) for v in calibration_scores.values()])
    return float(np.quantile(pooled, quantile))


@dataclass
class TrustDecision:
    """One candidate's flagging decision (spec.md §5.1: 'one criterion, shared
    across both cases' -- the *decision rule* below is identical whether the
    candidate came from the proposed pool or a live scenario request)."""

    per_kpi_scores: Dict[str, float]
    per_kpi_thresholds: Dict[str, float]
    tripped_kpis: List[str] = field(default_factory=list)

    @property
    def flagged(self) -> bool:
        """Mentor's decision rule: flag if ANY KPI falls below its threshold
        (spec.md §7 item 3) -- preserves one shared criterion even though
        calibration is per-KPI."""
        return bool(self.tripped_kpis)


def decide(per_kpi_trust_score: Dict[str, float], thresholds: Dict[str, float]) -> TrustDecision:
    """per_kpi_trust_score: {kpi_slug: trust_score(...)} for one candidate,
    already combining that KPI's UQ term with the candidate's shared novelty
    term. thresholds: from calibrate_thresholds_per_kpi() (default) or
    calibrate_threshold_global() (comparison variant, same threshold repeated
    per KPI by the caller).
    """
    missing = set(per_kpi_trust_score) - set(thresholds)
    if missing:
        raise KeyError(f"no threshold for KPIs: {sorted(missing)}")
    tripped = [kpi for kpi, score in per_kpi_trust_score.items() if score > thresholds[kpi]]
    return TrustDecision(
        per_kpi_scores=dict(per_kpi_trust_score),
        per_kpi_thresholds=dict(thresholds),
        tripped_kpis=tripped,
    )
