"""
Golden checks: assistant text should repeat key numeric facts from the snapshot (anti-hallucination tests).
"""

from __future__ import annotations

from typing import List

from llm_attribution.schema import AttributionSnapshot


def _variants(x: float) -> List[str]:
    s = f"{x:.6f}".rstrip("0").rstrip(".")
    out = {str(x), s, f"{x:.4f}", f"{x:.3f}", f"{x:.2f}"}
    return [o for o in out if o]


def golden_numeric_fidelity(
    assistant_text: str,
    snapshot: AttributionSnapshot,
    *,
    require_feature_names: bool = False,
) -> List[str]:
    """
    Return list of violation messages (empty if every checked number appears at least once).
    Checks headline metrics. Set ``require_feature_names=True`` for analyst-style answers that must cite features.
    """
    text = assistant_text
    violations: List[str] = []

    checks: List[tuple[str, List[str]]] = [
        ("test_rmse", _variants(snapshot.metrics.test_rmse)),
        ("test_r2", _variants(snapshot.metrics.test_r2)),
        ("interval full_width", _variants(snapshot.interval_90.full_width)),
        ("empirical_coverage", _variants(snapshot.interval_90.empirical_coverage)),
    ]
    for label, opts in checks:
        if any(o in text for o in opts):
            continue
        violations.append(f"Missing {label}: expected one of {opts[:4]}")

    if require_feature_names:
        for sf in snapshot.top_shap_features[:3]:
            if sf.name not in text:
                violations.append(f"Top SHAP feature name not mentioned: {sf.name!r}")

    return violations
