"""
Operator-console backend (technical report §13). Thin, UI-callable wrappers
over the batch-sequential loop that already exists -- no new ML logic, just
functions that return plain dicts instead of printing, so the HTTP layer in
run_ui_inference_api.py can expose them without duplicating the CLI code in
cli_export_manual_round.py / cli_ingest_manual_round.py /
cli_recalibrate_uq_methods.py.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from . import dataset_store, pending_queue
from .des_backend.manual_worklist import ManualWorklistDESBackend
from .kpi_scope import resolve_scope
from .loop import export_manual_round, ingest_manual_round
from .proven6 import PROVEN_6, get_proven_uq_estimator
from .recalibration_check import run_recalibration_check
from .results_validation import validate_results
from .uq.dispatch import load_registry


def _propose_random_candidates(
    X_train: pd.DataFrame, n: int, seed: Optional[int], tag: str
) -> pd.DataFrame:
    """v0 placeholder proposer (uniform-random per factor, spec.md §5.3).
    Index names are tagged with the round token so two rounds' candidates
    never collide in the append-only extended dataset."""
    import numpy as np

    rng = np.random.default_rng(seed)
    lo, hi = X_train.min(), X_train.max()
    rows = {f: rng.uniform(lo[f], hi[f], size=n) for f in X_train.columns}
    df = pd.DataFrame(rows)
    df.index = [f"cand_{tag}_{i:03d}" for i in range(n)]
    return df


# ────────────────────────────────────────────────────────────────────────
# Dataset status
# ────────────────────────────────────────────────────────────────────────

def dataset_status() -> Dict[str, Any]:
    X, Y = dataset_store.load_current_training_data()
    per_kpi = {col: int(Y[col].notna().sum()) for col in Y.columns}
    manifest = dataset_store.load_manifest()
    rounds = [
        {
            "round_id": e.get("round_id"),
            "status": e.get("status"),
            "kpi_scope": e.get("kpi_scope"),
            "exported_at": e.get("exported_at"),
            "ingested_at": e.get("ingested_at"),
            "n_rows_added": e.get("n_rows_added"),
            "n_training_rows_after": e.get("n_training_rows_after"),
            "flagged_run_ids": e.get("flagged_run_ids", []),
        }
        for e in manifest
    ]
    return {
        "n_training_rows": int(len(X)),
        "n_original_rows": int(len(X) - sum(r.get("n_rows_added") or 0 for r in rounds if r["status"] == "ingested")),
        "per_kpi_rows": per_kpi,
        "rounds": rounds,
        "pending_open": len(pending_queue.list_entries("open")),
    }


# ────────────────────────────────────────────────────────────────────────
# Pending-review queue
# ────────────────────────────────────────────────────────────────────────

def pending_list() -> Dict[str, Any]:
    return {"entries": pending_queue.list_entries("open")}


def pending_dismiss(entry_id: str) -> Dict[str, Any]:
    ok = pending_queue.set_status(entry_id, "dismissed")
    return {"ok": ok}


# ────────────────────────────────────────────────────────────────────────
# Build a round (export the worklist)
# ────────────────────────────────────────────────────────────────────────

def export_round(
    *,
    kpi_scope: str = "demo4",
    n_candidates: int = 20,
    quantile: float = 0.9,
    max_batch_size: int = 10,
    n_replications: int = 5,
    seed: Optional[int] = 42,
    candidate_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """propose -> score -> flag -> export. If candidate_ids is given, the
    candidate pool is drawn from those pending-queue entries; otherwise the
    v0 uniform-random proposer is used (documented placeholder)."""
    scope = kpi_scope.strip().lower()
    is_proven6 = scope == "proven6"
    kpi_slugs = list(PROVEN_6) if is_proven6 else resolve_scope(scope)
    estimator_factory = get_proven_uq_estimator if is_proven6 else None
    registry = load_registry()
    X_train, Y_train = dataset_store.load_current_training_data()

    round_id = dataset_store.new_round_id()
    tag = round_id.replace("round_", "")

    used_pending: List[str] = []
    if candidate_ids:
        entries = {e["id"]: e for e in pending_queue.list_entries("open")}
        picked = [entries[i] for i in candidate_ids if i in entries]
        if not picked:
            return {"flagged_count": 0, "message": "None of the selected pending entries are still open."}
        rows = {}
        for col in X_train.columns:
            rows[col] = [float(e["vector"].get(col, X_train[col].median())) for e in picked]
        candidate_pool = pd.DataFrame(rows)
        candidate_pool.index = [f"cand_{tag}_{i:03d}" for i in range(len(picked))]
        used_pending = [e["id"] for e in picked]
    else:
        candidate_pool = _propose_random_candidates(X_train, n_candidates, seed, tag)

    rdir = dataset_store.round_dir(round_id)
    rdir.mkdir(parents=True, exist_ok=True)
    out_stem = rdir / "run"

    manual_backend = ManualWorklistDESBackend()
    result = export_manual_round(
        kpi_slugs, candidate_pool, manual_backend, out_stem, X_train, Y_train,
        registry=registry, quantile=quantile, max_batch_size=max_batch_size,
        n_replications=n_replications, seed=seed, estimator_factory=estimator_factory,
    )

    if result["flagged_count"] == 0:
        return {"flagged_count": 0, "message": "Nothing flagged at this threshold -- no worklist produced."}

    dataset_store.record_round_exported(
        round_id, kpi_slugs, list(result["flagged_batch"].index), result["thresholds"],
        n_replications, seed, result["csv_path"], result["worklist_path"], kpi_scope=scope,
    )
    if used_pending:
        pending_queue.mark_batched(used_pending, round_id)

    return {
        "round_id": round_id,
        "flagged_count": int(result["flagged_count"]),
        "kpi_scope": scope,
        "kpi_slugs": kpi_slugs,
        "flagged_run_ids": list(result["flagged_batch"].index),
        "run_requests_csv": str(result["csv_path"]),
        "worklist_xlsx": str(result["worklist_path"]),
    }


def worklist_bytes(round_id: str) -> Optional[bytes]:
    entry = next((e for e in dataset_store.load_manifest() if e["round_id"] == round_id), None)
    if entry is None:
        return None
    p = Path(entry.get("worklist_xlsx", ""))
    return p.read_bytes() if p.is_file() else None


# ────────────────────────────────────────────────────────────────────────
# Ingest results
# ────────────────────────────────────────────────────────────────────────

def ingest_round(
    round_id: str,
    results_csv_text: Optional[str] = None,
    results_content_b64: Optional[str] = None,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    """Two ways in, same underlying file write (6-Sep finding): a real
    AnyLogic Cloud export is normally an .xlsx, not a .csv -- the UI
    originally only accepted pasted/typed CSV text (results_csv_text,
    written with write_text()), which silently corrupts a real .xlsx
    upload (a binary, zip-based format) if it's ever routed through it.
    results_content_b64 + filename is the real-file path: the raw bytes,
    base64-encoded for the JSON transport, written back out with
    write_bytes() under the UPLOADED file's own extension so
    ManualWorklistDESBackend.ingest_results() -- already .csv/.xlsx-aware,
    same as the CLI path -- picks the right parser. results_csv_text
    stays supported for the "paste CSV text into the textarea" case,
    which is genuinely plain text and never needs this."""
    if results_csv_text is None and results_content_b64 is None:
        return {"ok": False, "error": "No results provided -- paste CSV text or choose a file."}

    manifest = dataset_store.load_manifest()
    entry = next((e for e in manifest if e["round_id"] == round_id), None)
    if entry is None:
        return {"ok": False, "error": f"No round {round_id!r} -- export it first."}
    if entry["status"] == "ingested":
        return {"ok": False, "error": f"Round {round_id} was already ingested at {entry.get('ingested_at')}."}

    rdir = dataset_store.round_dir(round_id)
    rdir.mkdir(parents=True, exist_ok=True)

    if results_content_b64 is not None:
        try:
            raw_bytes = base64.b64decode(results_content_b64, validate=True)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": f"Uploaded file could not be decoded: {e}"}
        # 6-Sep finding #2: a real export was named "*.csv" but its actual
        # content was a genuine .xlsx (a ZIP archive) -- the extension
        # lied. Trusting Path(filename).suffix alone would have handed
        # binary ZIP bytes to pandas.read_csv and failed or produced
        # garbage. .xlsx/.xls files always start with a recognisable
        # magic number regardless of what they're named, so sniff that
        # FIRST and only fall back to the filename's own extension when
        # the content doesn't look like a spreadsheet binary at all
        # (i.e. it's plausibly real CSV text).
        ZIP_MAGIC = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")  # .xlsx (zip-based)
        OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # legacy .xls (OLE2)
        if raw_bytes[:4] in ZIP_MAGIC:
            suffix = ".xlsx"
        elif raw_bytes[:8] == OLE_MAGIC:
            suffix = ".xls"
        else:
            suffix = Path(filename).suffix.lower() if filename else ""
            if suffix not in (".csv", ".xlsx", ".xls"):
                suffix = ".csv"  # content doesn't look like a spreadsheet binary -- treat as text
        results_path = rdir / f"results{suffix}"
        results_path.write_bytes(raw_bytes)
    else:
        results_path = rdir / "results.csv"
        results_path.write_text(results_csv_text)

    kpi_slugs = entry["kpi_slugs"]
    kpi_scope = entry.get("kpi_scope", "demo4")
    estimator_factory = get_proven_uq_estimator if kpi_scope == "proven6" else None
    registry = load_registry()
    manual_backend = ManualWorklistDESBackend()

    flagged_batch = manual_backend.import_run_requests_csv(Path(entry["run_requests_csv"]))
    X_train, Y_train = dataset_store.load_current_training_data()

    parsed = manual_backend.ingest_results(results_path)
    warnings = validate_results(parsed, Y_train, registry)

    result = ingest_manual_round(
        kpi_slugs, results_path, manual_backend, flagged_batch, X_train, Y_train, registry,
        estimator_factory=estimator_factory,
    )
    X_new = result["X_train"].loc[flagged_batch.index]
    Y_new = result["Y_train"].loc[flagged_batch.index]
    dataset_store.append_round(X_new, Y_new)
    dataset_store.record_round_ingested(
        round_id, results_path, n_rows_added=len(X_new),
        n_training_rows_after=result["n_training_rows_after"],
    )

    ingested_kpis = [c for c in parsed.columns if c not in {"run_id", "replication", "seed"}]
    return {
        "ok": True,
        "round_id": round_id,
        "rows_added": int(len(X_new)),
        "n_training_rows_after": int(result["n_training_rows_after"]),
        "ingested_kpi_columns": ingested_kpis,
        "warnings": list(warnings),
    }


# ────────────────────────────────────────────────────────────────────────
# Recalibration check
# ────────────────────────────────────────────────────────────────────────

def recalibration_report() -> Dict[str, Any]:
    checks = run_recalibration_check()
    rows = []
    for c in checks:
        rows.append({
            "kpi_slug": c.kpi_slug,
            "family": c.registered_as,
            "n_train": c.n_train,
            "n_test": c.n_test,
            "fixed_method": c.current_method,
            "best_method": c.recommended_method,
            "review_needed": bool(c.changed),
            "methods": [
                {
                    "name": m.method,
                    "coverage": float(m.coverage),
                    "mean_width": float(m.mean_width),
                    "rmse": float(m.rmse),
                }
                for m in c.results
            ],
        })
    return {"checks": rows, "review_count": sum(1 for r in rows if r["review_needed"])}
