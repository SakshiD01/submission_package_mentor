"""
T2.13 (spec.md §7 item 15): self-service sanity checks on a manual round's
real results, run automatically before they're trusted -- no mentor needed
to catch this class of problem.

Built in direct response to a real incident (5-Sep): a real AnyLogic Cloud
export for a genuine DEMO_4 batch had 4 KPIs (all four outbound-agri/AP
waiting times) read exactly 0.000 for every one of 10 candidates. Traced to
a real, defensible mechanical cause (every "customs intervention time"
constant in the confirmed AS-IS baseline is 0 -- see
AnyLogic_Constants_Worklist.xlsx), not obviously a data-entry mistake, but
NOT something a human skimming a spreadsheet of 20 columns x 10 rows would
reliably notice either. This module is the check that should have flagged
it immediately, and now will for every future round.

Two checks, both cheap and both would have caught the 5-Sep incident:
  - a KPI column where every value in the new batch is identical (the
    2 KPI values landing on the SAME repeated number is already suspicious;
    an entire batch is a near-certain signal something upstream is fixed
    when it shouldn't be)
  - a KPI column whose new values sit far outside the historical [min, max]
    range from the current training data (catches the opposite failure mode
    -- values that are wildly implausible rather than suspiciously flat)

Deliberately NOT blocking: a genuinely rare but real KPI value (spec.md §7
item 14's SVR outlier discussion is the exact precedent) should still be
ingested, not rejected by an automated gate. This surfaces a warning for a
human to read, it does not refuse to ingest.
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


def validate_results(
    new_results: pd.DataFrame,
    historical_Y: pd.DataFrame,
    registry: Dict[str, Any],
    out_of_range_factor: float = 0.5,
) -> List[str]:
    """new_results: slug-named columns (post col_to_slug, as returned by
    ManualWorklistDESBackend.ingest_results()), one row per replication.
    historical_Y: raw_key-named columns, the CURRENT training data (before
    this round is appended) -- what "normal" looks like so far.
    out_of_range_factor: a new value beyond
    [min - factor*range, max + factor*range] is flagged (0.5 = up to 50%
    beyond the historical span in either direction before it's suspicious).

    Returns a list of human-readable warning strings -- empty if nothing
    looked wrong. Does not raise; the caller decides what to do with them.
    """
    warnings: List[str] = []
    outputs = registry.get("outputs", {})
    meta_cols = {"run_id", "replication", "seed"}
    kpi_cols = [c for c in new_results.columns if c not in meta_cols]

    for slug in kpi_cols:
        if slug not in outputs:
            continue  # dispatch.py's own KeyError elsewhere is the right place to fail on this
        raw_key = outputs[slug]["raw_key"]
        if raw_key not in historical_Y.columns:
            continue

        new_vals = new_results[slug].to_numpy(dtype=float)
        new_vals = new_vals[~np.isnan(new_vals)]
        if len(new_vals) == 0:
            continue

        if np.allclose(new_vals, new_vals[0]) and len(new_vals) > 1:
            warnings.append(
                f"{slug} ({raw_key}): every one of {len(new_vals)} new values is identical "
                f"({new_vals[0]:.4g}) -- check whether an upstream input that should vary per "
                f"candidate was actually held fixed, or a governing constant unexpectedly forces this to a single value."
            )

        hist = historical_Y[raw_key].to_numpy(dtype=float)
        hist = hist[~np.isnan(hist)]
        if len(hist) == 0:
            continue
        lo, hi = hist.min(), hist.max()
        span = hi - lo
        margin = out_of_range_factor * span if span > 0 else abs(lo) * out_of_range_factor or 1.0
        low_bound, high_bound = lo - margin, hi + margin
        outliers = new_vals[(new_vals < low_bound) | (new_vals > high_bound)]
        if len(outliers) > 0:
            warnings.append(
                f"{slug} ({raw_key}): {len(outliers)} of {len(new_vals)} new value(s) fall outside "
                f"the historical range [{lo:.4g}, {hi:.4g}] by more than {out_of_range_factor:.0%} of that "
                f"range -- e.g. {outliers[0]:.4g}. Could be a genuinely novel scenario (fine, ingest it) "
                f"or a unit/mapping mismatch (check before trusting it)."
            )

    return warnings
