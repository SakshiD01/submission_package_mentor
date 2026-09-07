"""
T2.11 (spec.md §7 item 12): CLI entrypoint for the export half of a manual
AnyLogic Cloud round -- propose -> score -> flag -> batch -> export.

This is the actual trigger for export_manual_round() (loop.py) -- until
this script existed, running that step meant writing a one-off Python
snippet by hand each time, which isn't reproducible or something a mentor
could re-run. This script is.

Candidate proposal (v0, documented limitation, not a real active-learning
design): if --candidates-csv isn't given, candidates are drawn UNIFORMLY AT
RANDOM within each of the 35 factors' observed min/max range across the
CURRENT training data (original 129 + every manual round so far). This is
a placeholder, not a diversity-aware or uncertainty-directed proposal
strategy (spec.md Task 1 §4.1 item 4 names greedy max-min / DPP-style batch
selection as the real target) -- flagged as future extension work, not
pretended to be more than it is.

Run (from experimenting_ml/src -- this is a package submodule, run with -m):
    cd experimenting_ml/src
    python -m loop.cli_export_manual_round
    python -m loop.cli_export_manual_round --candidates-csv my_candidates.csv --n-replications 5 --seed 42
    python -m loop.cli_export_manual_round --n-candidates 20 --max-batch-size 8 --kpi-scope all20
    python -m loop.cli_export_manual_round --kpi-scope proven6 --n-candidates 20 --seed 42

--kpi-scope proven6 (spec.md §7 item 13): runs this same machinery against
PROVEN_6 -- the 6 KPIs with an empirically benchmarked, evidence-backed UQ
method choice (UQ_Method_Benchmark.xlsx), using proven6.get_proven_uq_estimator
instead of the generic dispatch. Fully separate from DEMO_4 -- never mixed
within one round, and the manifest records which kpi_scope a round used so
cli_ingest_manual_round.py automatically retrains with the matching mechanism.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from . import dataset_store
from .des_backend.manual_worklist import ManualWorklistDESBackend
from .kpi_scope import resolve_scope
from .loop import export_manual_round
from .proven6 import PROVEN_6, get_proven_uq_estimator
from .uq.dispatch import load_registry

_HERE = Path(__file__).resolve().parent


def propose_random_candidates(X_train: pd.DataFrame, n: int, seed: Optional[int]) -> pd.DataFrame:
    """v0 placeholder proposal strategy -- see module docstring. Uniform
    random within each factor's observed [min, max], not diversity-aware."""
    rng = np.random.default_rng(seed)
    lo = X_train.min()
    hi = X_train.max()
    rows = {factor: rng.uniform(lo[factor], hi[factor], size=n) for factor in X_train.columns}
    df = pd.DataFrame(rows)
    df.index = [f"proposed_{i:04d}" for i in range(n)]
    return df


def main(argv: Optional[List[str]] = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--kpi-scope", default="demo4", help="'demo4' (default, core DoD) or 'all20' or 'proven6'")
    p.add_argument("--candidates-csv", type=Path, default=None,
                    help="CSV of 35 factor-named columns to propose from; if omitted, "
                         "--n-candidates random candidates are generated instead (v0 placeholder)")
    p.add_argument("--n-candidates", type=int, default=20,
                    help="how many random candidates to propose if --candidates-csv is not given")
    p.add_argument("--quantile", type=float, default=0.9, help="per-KPI threshold calibration quantile")
    p.add_argument("--max-batch-size", type=int, default=10, help="cap on flagged candidates per round")
    p.add_argument("--n-replications", type=int, default=5,
                    help="DES replications per run (default 5, matches the mentor-confirmed real process)")
    p.add_argument("--seed", type=int, default=None, help="reproducibility seed")
    p.add_argument("--out-dir", type=Path, default=_HERE.parent.parent / "data" / "manual_rounds",
                    help="base directory a new round's files are written under (default: matches dataset_store)")
    args = p.parse_args(argv)

    is_proven6 = args.kpi_scope.strip().lower() == "proven6"
    kpi_slugs = list(PROVEN_6) if is_proven6 else resolve_scope(args.kpi_scope)
    estimator_factory = get_proven_uq_estimator if is_proven6 else None
    registry = load_registry()
    X_train, Y_train = dataset_store.load_current_training_data()

    if args.candidates_csv is not None:
        candidate_pool = pd.read_csv(args.candidates_csv, index_col=0)
    else:
        candidate_pool = propose_random_candidates(X_train, args.n_candidates, args.seed)

    round_id = dataset_store.new_round_id()
    round_dir = args.out_dir / round_id
    round_dir.mkdir(parents=True, exist_ok=True)
    out_stem = round_dir / "run"

    manual_backend = ManualWorklistDESBackend()
    result = export_manual_round(
        kpi_slugs, candidate_pool, manual_backend, out_stem, X_train, Y_train,
        registry=registry, quantile=args.quantile, max_batch_size=args.max_batch_size,
        n_replications=args.n_replications, seed=args.seed, estimator_factory=estimator_factory,
    )

    if result["flagged_count"] == 0:
        print(f"[{round_id}] Nothing flagged at quantile={args.quantile} -- no worklist produced.")
        print("Try a lower --quantile, more --n-candidates, or check the candidate pool covers a novel region.")
        return

    dataset_store.record_round_exported(
        round_id, kpi_slugs, list(result["flagged_batch"].index), result["thresholds"],
        args.n_replications, args.seed, result["csv_path"], result["worklist_path"],
        kpi_scope=args.kpi_scope.strip().lower(),
    )

    print(f"Round {round_id}: {result['flagged_count']} candidate(s) flagged.")
    print(f"  Run request CSV : {result['csv_path']}")
    print(f"  Worksheet (xlsx): {result['worklist_path']}")
    print(f"  Manifest        : {dataset_store.MANIFEST_PATH}")
    print()
    print("Next step: run these in AnyLogic Cloud by hand, export results as CSV/Excel, then:")
    print(f"  python -m loop.cli_ingest_manual_round --round-id {round_id} --results <path_to_results>")


if __name__ == "__main__":
    main(sys.argv[1:])
