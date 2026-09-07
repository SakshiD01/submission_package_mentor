"""
SyntheticDESBackend (spec.md §5.2, §5.3): a GP fit to the real 129x35x20 data
as a stand-in ground truth, sampled with injected replication noise to
emulate a new AnyLogic run without a human in the loop.

Replication-level output (not averaged) by design, matching the mentor's
confirmed ManualWorklistDESBackend import contract (spec.md §7 item 2,
resolved 25-Aug-2026: "one row per replication ... important so we can
separate DES stochastic noise from surrogate uncertainty"). Both backends
return the same shape so retrain/recalibrate code (T2.7) is written once.

Ground truth (`ground_truth_fns`) and noise calibration (`noise_std`) are
injected rather than fit in this class -- that's T2.2's job (Sakshi,
25-26 Aug: fit a GP per KPI to the real 129 rows, calibrate noise_std from
each KPI's own CV/test residual RMSE). This class owns the sampling
mechanics only, which don't depend on T2.2 landing first and are real,
tested code today.

`n_replications` defaults to 5 (spec.md §7 item 5, mentor-confirmed 27-Aug:
each of the 129 original NOLHC points is itself the average of 5 real DES
replications) -- matching the real process's structure rather than an
arbitrary placeholder. This does not make the injected per-replication
noise itself measured (still §7 item 5's documented assumption; the raw
per-replication values behind those 129 means were never retained), only
the replication COUNT is a confirmed fact now.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from .base import DESBackend

GroundTruthFn = Callable[[np.ndarray], np.ndarray]  # X (n, 35) -> y (n,)


class SyntheticDESBackend(DESBackend):
    def __init__(
        self,
        kpi_slugs: List[str],
        ground_truth_fns: Dict[str, GroundTruthFn],
        noise_std: Dict[str, float],
    ) -> None:
        missing_gt = set(kpi_slugs) - set(ground_truth_fns)
        missing_noise = set(kpi_slugs) - set(noise_std)
        if missing_gt:
            raise KeyError(f"no ground_truth_fn for KPIs: {sorted(missing_gt)}")
        if missing_noise:
            raise KeyError(f"no noise_std for KPIs: {sorted(missing_noise)}")
        if any(s < 0 for s in noise_std.values()):
            raise ValueError(f"noise_std must be non-negative: {noise_std}")

        self.kpi_slugs = list(kpi_slugs)
        self.ground_truth_fns = ground_truth_fns
        self.noise_std = noise_std

    def simulate(
        self,
        candidate_points: pd.DataFrame,
        n_replications: int = 5,  # matches the real process (mentor-confirmed 27-Aug, spec.md §7 item 5)
        seed: Optional[int] = None,
    ) -> pd.DataFrame:
        """One row per (candidate, replication) -- spec.md §7 item 2's import
        shape: run_id, replication, seed, then one column per KPI.

        candidate_points: rows of the 35 NOLHC input columns. Its index is
        used as run_id (caller sets a meaningful index -- e.g. a batch's
        proposal IDs); AnyLogic-name translation for the real backend is a
        separate, not-yet-built concern (spec.md §7 item 1's open mapping
        question), not something this synthetic backend needs to solve.
        """
        if n_replications < 1:
            raise ValueError(f"n_replications must be >= 1, got {n_replications}")
        if candidate_points.empty:
            raise ValueError("candidate_points is empty")

        X = candidate_points.to_numpy(dtype=float)
        n_candidates = X.shape[0]

        # One independent seed per (candidate, replication) so noise draws
        # are reproducible and don't silently correlate across replications --
        # SeedSequence.spawn() is the numpy-recommended way to do this safely.
        root_ss = np.random.SeedSequence(seed)
        child_seeds = root_ss.spawn(n_candidates * n_replications)

        rows = []
        seed_idx = 0
        for cand_pos in range(n_candidates):
            run_id = candidate_points.index[cand_pos]
            x_row = X[cand_pos : cand_pos + 1]  # keep 2D for ground_truth_fns
            for replication in range(1, n_replications + 1):
                child_seed = child_seeds[seed_idx]
                seed_idx += 1
                rng = np.random.default_rng(child_seed)

                row: Dict[str, object] = {
                    "run_id": run_id,
                    "replication": replication,
                    "seed": int(child_seed.generate_state(1)[0]),
                }
                for kpi in self.kpi_slugs:
                    mean = float(self.ground_truth_fns[kpi](x_row)[0])
                    noise = float(rng.normal(0.0, self.noise_std[kpi]))
                    row[kpi] = mean + noise
                rows.append(row)

        return pd.DataFrame(rows)
