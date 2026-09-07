"""
CLI for recalibration_check.py (spec.md §9 follow-up, 5-Sep). Read-only --
never writes to proven6.py. Run this after any manual round is ingested (or
periodically once the loop is automated) to see whether the dataset's
growth has changed which UQ method is closest to the 90% coverage target
for any PROVEN_6 KPI.

Run (from experimenting_ml/src):
    python -m loop.cli_recalibrate_uq_methods
"""

from __future__ import annotations

import sys
from typing import List, Optional

from .proven6 import PROVEN_METHOD
from .recalibration_check import METHOD_LABELS, TARGET_COVERAGE, KPICheck, run_recalibration_check


def _format_check(check: KPICheck) -> str:
    lines = [
        f"{check.kpi_slug} ({check.registered_as}) -- n_train={check.n_train}, n_test={check.n_test}",
        f"  currently fixed : {check.current_method} ({METHOD_LABELS.get(check.current_method, check.current_method)})",
    ]
    for r in sorted(check.results, key=lambda r: abs(r.coverage - TARGET_COVERAGE)):
        marker = " <- closest to target" if r.method == check.recommended_method else ""
        lines.append(
            f"    {r.method:<20} coverage={r.coverage:5.1%}  mean_width={r.mean_width:8.4g}  rmse={r.rmse:8.4g}{marker}"
        )
    if check.changed:
        lines.append(
            f"  ** REVIEW NEEDED ** -- on the current dataset, {check.recommended_method!r} is now "
            f"closer to the 90% target than the fixed method {check.current_method!r}. "
            f"NOT auto-applied -- proven6.PROVEN_METHOD is unchanged. Take this to the mentor "
            f"before changing it, same as the original 1-Sep decision."
        )
    else:
        lines.append(f"  OK -- {check.current_method!r} is still the closest to target. No change recommended.")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> None:
    checks = run_recalibration_check()
    print(f"PROVEN_6 recalibration check -- target coverage {TARGET_COVERAGE:.0%}\n")
    for check in checks:
        print(_format_check(check))
        print()

    changed = [c for c in checks if c.changed]
    if changed:
        print(f"SUMMARY: {len(changed)}/{len(checks)} KPI(s) would recommend a different method -- "
              f"review before touching proven6.py: {[c.kpi_slug for c in changed]}")
    else:
        print(f"SUMMARY: all {len(checks)} PROVEN_6 methods still match their currently fixed choice. "
              f"No mentor review needed from this check.")


if __name__ == "__main__":
    main(sys.argv[1:])
