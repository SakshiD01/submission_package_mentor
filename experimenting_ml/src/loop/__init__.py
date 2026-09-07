"""
Uncertainty-aware, batch-sequential retraining loop (spec.md §5, Task 2).

Layout (spec.md §5.4):
    uq/            -- UQEstimator interface + the three dispatch paths (spec.md §5.1)
    des_backend/   -- DESBackend interface; SyntheticDESBackend now, ManualWorklistDESBackend later
    kpi_scope.py   -- the two-tier KPI lists (spec.md §5.1.1): DEMO_4 / ALL_20
    novelty.py     -- OOD/novelty scorer (spec.md §5.1)
    trust.py       -- trust_score(): UQ term + novelty term, one criterion (spec.md §5.1)
    loop.py        -- orchestrator: propose -> score -> batch -> simulate -> retrain -> recalibrate (spec.md §5.3)

Status as of T2.1 (24-25 Aug 2026): interfaces + registry-driven dispatch are implemented and
tested. Estimator/backend/loop *bodies* are stubs, filled in on their scheduled days
(T2.3 26-27 Aug, T2.4 27-28 Aug, T2.5 28 Aug, T2.6 29 Aug, T2.7 30 Aug) per spec.md §6.
"""

from __future__ import annotations
