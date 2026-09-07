"""
DESBackend interface (spec.md §5.3): "run DES" as a swappable simulate() call
so loop.py never knows whether it's talking to the synthetic stand-in or,
eventually, a real AnyLogic-backed worklist.

    SyntheticDESBackend        -- v0, T2.5 (28 Aug): grounded in a GP fit to
                                   the real 129-run data (spec.md §5.2)
    ManualWorklistDESBackend   -- future: export candidate rows in the
                                   ExpValues layout, ingest back the SimResults
                                   a human ran in AnyLogic (spec.md §2, DES access row)
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class DESBackend(Protocol):
    def simulate(self, candidate_points: pd.DataFrame) -> pd.DataFrame:
        """candidate_points: rows of the 35 NOLHC input columns.

        Returns a DataFrame with the same row index plus one column per
        simulated KPI slug -- same shape a real AnyLogic SimResults export
        would have, so downstream retrain code doesn't care which backend ran.
        """
        ...
