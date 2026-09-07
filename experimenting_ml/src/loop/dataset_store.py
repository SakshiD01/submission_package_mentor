"""
T2.10 (spec.md §7 item 12): persistent, append-only home for the growing
training set, plus a round-by-round manifest -- the piece that makes the
manual loop actually reproducible rather than a one-off in-memory
DataFrame that vanishes when the Python process exits.

The original 129 rows (nolhc_ml/data/processed/X_train.parquet /
Y_train.parquet) are treated as READ-ONLY -- never written to by this
module. Every manual round's new rows accumulate separately in
experimenting_ml/data/manual_rounds/, and load_current_training_data()
transparently returns "the original 129 + everything appended so far" so
downstream code (loop.py, the UQ estimators) never has to know how many
rounds have happened. This keeps the original a stable, always-recoverable
baseline -- rerunning the whole loop from scratch just means deleting the
manual_rounds directory, not re-sourcing the 129 from the mentor's xlsx.

Layout:
    experimenting_ml/data/manual_rounds/
        rounds_manifest.json      -- append-only log, one entry per round
        extended_X_train.parquet  -- all manually-added candidate rows (35 cols)
        extended_Y_train.parquet  -- their real, ingested KPI results
        <round_id>/
            run_requests.csv      -- copy of what was exported (T2.9)
            worklist.xlsx         -- copy of the human worksheet (T2.9)
            results.csv           -- copy of what was ingested, for audit
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[2]
MANUAL_ROUNDS_DIR = _HERE.parents[1] / "data" / "manual_rounds"
MANIFEST_PATH = MANUAL_ROUNDS_DIR / "rounds_manifest.json"
EXTENDED_X_PATH = MANUAL_ROUNDS_DIR / "extended_X_train.parquet"
EXTENDED_Y_PATH = MANUAL_ROUNDS_DIR / "extended_Y_train.parquet"


def new_round_id() -> str:
    """Timestamp-based, chronologically sortable, human-readable."""
    return "round_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def round_dir(round_id: str) -> Path:
    return MANUAL_ROUNDS_DIR / round_id


def load_manifest() -> List[Dict[str, Any]]:
    if not MANIFEST_PATH.is_file():
        return []
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_manifest(entries: List[Dict[str, Any]]) -> None:
    MANUAL_ROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def record_round_exported(
    round_id: str,
    kpi_slugs: List[str],
    flagged_ids: List[str],
    thresholds: Dict[str, float],
    n_replications: int,
    seed: Optional[int],
    csv_path: Path,
    worklist_path: Path,
    kpi_scope: str = "demo4",
) -> None:
    """Called right after export_manual_round() succeeds -- logs a
    "pending" round before any human has touched AnyLogic, so a manifest
    entry always exists even if the ingest step happens days later.

    kpi_scope: which KPI set/estimator mechanism this round used ("demo4",
    "all20", or "proven6", spec.md §7 item 13) -- recorded so
    cli_ingest_manual_round.py can automatically retrain with the matching
    mechanism later, rather than requiring the human to remember and repeat
    it correctly days after the fact."""
    entries = load_manifest()
    entries.append({
        "round_id": round_id,
        "status": "exported_pending_manual_run",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "kpi_scope": kpi_scope,
        "kpi_slugs": kpi_slugs,
        "flagged_run_ids": flagged_ids,
        "thresholds": thresholds,
        "n_replications": n_replications,
        "seed": seed,
        "run_requests_csv": str(csv_path),
        "worklist_xlsx": str(worklist_path),
    })
    _save_manifest(entries)


def record_round_ingested(
    round_id: str,
    results_path: Path,
    n_rows_added: int,
    n_training_rows_after: int,
) -> None:
    """Called right after append_round() succeeds -- flips the manifest
    entry from "pending" to "complete" and records what actually landed."""
    entries = load_manifest()
    for entry in entries:
        if entry["round_id"] == round_id:
            entry["status"] = "ingested"
            entry["ingested_at"] = datetime.now(timezone.utc).isoformat()
            entry["results_csv"] = str(results_path)
            entry["n_rows_added"] = n_rows_added
            entry["n_training_rows_after"] = n_training_rows_after
            _save_manifest(entries)
            return
    raise KeyError(f"No manifest entry for round_id={round_id!r} -- was it exported first?")


def load_current_training_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """The original 129 (read-only) + every manually-added row appended so
    far. This is what run_loop()/export_manual_round() should be called
    with from the second round onward -- always the FULL current dataset,
    not just the original 129."""
    import sys

    sys.path.insert(0, str(_REPO_ROOT / "experimenting_ml" / "src"))
    from data import load_xy

    X0, Y0 = load_xy()
    if not (EXTENDED_X_PATH.is_file() and EXTENDED_Y_PATH.is_file()):
        return X0, Y0

    X_ext = pd.read_parquet(EXTENDED_X_PATH)
    Y_ext = pd.read_parquet(EXTENDED_Y_PATH)
    overlap = set(X0.index) & set(X_ext.index)
    if overlap:
        raise ValueError(f"extended dataset index collides with the original 129: {sorted(overlap)[:5]}")
    return pd.concat([X0, X_ext]), pd.concat([Y0, Y_ext])


def append_round(X_new: pd.DataFrame, Y_new: pd.DataFrame) -> None:
    """Persists new candidate rows + their real ingested KPI results to the
    extended dataset. Additive only -- never touches the original 129."""
    if X_new.empty or Y_new.empty:
        raise ValueError("X_new/Y_new must not be empty")
    if list(X_new.index) != list(Y_new.index):
        raise ValueError("X_new and Y_new must share the same index (run_id)")

    # Caught by test_dataset_store.py: checking only against prior manual
    # rounds isn't enough -- a round's run_ids must also not collide with
    # the ORIGINAL 129's index (plain integers 0-128), not just each other.
    import sys

    sys.path.insert(0, str(_REPO_ROOT / "experimenting_ml" / "src"))
    from data import load_xy

    X0, _ = load_xy()
    original_overlap = set(X0.index) & set(X_new.index)
    if original_overlap:
        raise ValueError(f"round's run_ids collide with the original 129's index: {sorted(original_overlap)}")

    MANUAL_ROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    if EXTENDED_X_PATH.is_file() and EXTENDED_Y_PATH.is_file():
        X_prev = pd.read_parquet(EXTENDED_X_PATH)
        Y_prev = pd.read_parquet(EXTENDED_Y_PATH)
        overlap = set(X_prev.index) & set(X_new.index)
        if overlap:
            raise ValueError(f"round's run_ids already exist in the extended dataset: {sorted(overlap)}")
        X_all = pd.concat([X_prev, X_new])
        Y_all = pd.concat([Y_prev, Y_new])
    else:
        X_all, Y_all = X_new, Y_new

    X_all.to_parquet(EXTENDED_X_PATH)
    Y_all.to_parquet(EXTENDED_Y_PATH)
