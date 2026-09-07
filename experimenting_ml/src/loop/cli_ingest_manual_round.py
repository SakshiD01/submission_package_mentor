"""
T2.11 (spec.md §7 item 12): CLI entrypoint for the ingest half of a manual
AnyLogic Cloud round -- real results in -> retrain -> persist -> log.

Run once the human running AnyLogic Cloud brings back their results export
for a round previously produced by cli_export_manual_round.py. Recovers
that round's candidate values from its own run_requests.csv (so nothing
has to be kept in memory across the two separate invocations, which could
be days apart -- spec.md §7 item 9), appends the real results to the
persistent extended training set (dataset_store.py), and updates the
round's manifest entry from "exported_pending_manual_run" to "ingested".

Run (from experimenting_ml/src):
    cd experimenting_ml/src
    python -m loop.cli_ingest_manual_round --round-id round_20260830_143000 --results ~/Downloads/anylogic_results.csv
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import List, Optional

from . import dataset_store
from .des_backend.manual_worklist import ManualWorklistDESBackend
from .loop import ingest_manual_round
from .proven6 import get_proven_uq_estimator
from .results_validation import validate_results
from .uq.dispatch import load_registry


def main(argv: Optional[List[str]] = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--round-id", required=True, help="the round_id printed by cli_export_manual_round.py")
    p.add_argument("--results", type=Path, required=True,
                    help="the AnyLogic Cloud results export (CSV or Excel) the human brought back")
    args = p.parse_args(argv)

    manifest = dataset_store.load_manifest()
    entry = next((e for e in manifest if e["round_id"] == args.round_id), None)
    if entry is None:
        raise SystemExit(f"No manifest entry for round_id={args.round_id!r} -- was cli_export_manual_round.py run first?")
    if entry["status"] == "ingested":
        raise SystemExit(f"Round {args.round_id} was already ingested at {entry.get('ingested_at')} -- refusing to double-count it.")

    kpi_slugs = entry["kpi_slugs"]
    # Auto-selected from what the export step recorded (spec.md §7 item 13) --
    # not a CLI flag, so retraining can never accidentally use a different
    # mechanism than the round was actually exported/flagged with.
    kpi_scope = entry.get("kpi_scope", "demo4")
    estimator_factory = get_proven_uq_estimator if kpi_scope == "proven6" else None
    registry = load_registry()
    manual_backend = ManualWorklistDESBackend()

    round_dir = dataset_store.round_dir(args.round_id)
    run_requests_path = Path(entry["run_requests_csv"])
    flagged_batch = manual_backend.import_run_requests_csv(run_requests_path)

    X_train, Y_train = dataset_store.load_current_training_data()

    # T2.13 (spec.md §7 item 15): sanity-check the real results BEFORE they're
    # trusted -- built in direct response to the 5-Sep incident (4 KPIs
    # silently reading 0.000 across a whole real batch). Warns, does not
    # block -- a genuinely rare real value should still be ingested.
    parsed_results = manual_backend.ingest_results(args.results)
    warnings = validate_results(parsed_results, Y_train, registry)
    if warnings:
        print(f"CAUTION -- {len(warnings)} sanity-check warning(s) on this round's results (not blocking ingestion):")
        for w in warnings:
            print(f"  - {w}")
        print()

    result = ingest_manual_round(
        kpi_slugs, args.results, manual_backend, flagged_batch, X_train, Y_train, registry,
        estimator_factory=estimator_factory,
    )

    X_new = result["X_train"].loc[flagged_batch.index]
    Y_new = result["Y_train"].loc[flagged_batch.index]
    dataset_store.append_round(X_new, Y_new)

    # audit trail: keep a copy of the actual results file alongside this round's other artifacts
    round_dir.mkdir(parents=True, exist_ok=True)
    results_copy = round_dir / f"results{args.results.suffix}"
    shutil.copy(args.results, results_copy)

    dataset_store.record_round_ingested(
        args.round_id, results_copy, n_rows_added=len(X_new),
        n_training_rows_after=result["n_training_rows_after"],
    )

    print(f"Round {args.round_id} ingested.")
    print(f"  Rows added          : {len(X_new)}")
    print(f"  Training set size   : {result['n_training_rows_before']} -> {result['n_training_rows_after']}")
    print(f"  KPI columns kept    : {sorted(c for c in result['Y_train'].columns)}")
    print(f"  Estimators refit for: {sorted(result['estimators'])}")
    print(f"  Persisted to        : {dataset_store.EXTENDED_X_PATH}, {dataset_store.EXTENDED_Y_PATH}")
    print(f"  Results archived to : {results_copy}")


if __name__ == "__main__":
    main(sys.argv[1:])
