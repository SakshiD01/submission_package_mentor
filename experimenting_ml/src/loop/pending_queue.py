"""
Pending-review queue for the operator console (technical report §13).

When a live scenario query scores low-trust, its input vector is appended
here so a backend operator can later triage it and, if worth a real
simulation, roll it into a manual AnyLogic round. This is the reactive
half of spec.md §5.3's "both entry points feed the same trust-score
function" -- the proactive half is cli_export_manual_round's random
proposer.

Storage: a single JSON file under experimenting_ml/data/operator/. Small,
append-mostly, human-inspectable. Not the training set -- nothing here is
trusted data, only candidates awaiting a decision.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_HERE = Path(__file__).resolve().parent
QUEUE_DIR = _HERE.parents[1] / "data" / "operator"
QUEUE_PATH = QUEUE_DIR / "pending_queue.json"

_LOCK = threading.Lock()

# de-dupe: two vectors within this relative tolerance on every factor are "the same point"
_DEDUPE_RTOL = 1e-3
# hard cap so a busy simulator can't grow the file without bound
_MAX_OPEN = 500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> List[Dict[str, Any]]:
    if not QUEUE_PATH.is_file():
        return []
    try:
        with QUEUE_PATH.open() as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save(entries: List[Dict[str, Any]]) -> None:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = QUEUE_PATH.with_suffix(".json.tmp")
    with tmp.open("w") as fh:
        json.dump(entries, fh, indent=2)
    tmp.replace(QUEUE_PATH)


def _same_point(a: Dict[str, float], b: Dict[str, float]) -> bool:
    keys = set(a) | set(b)
    for k in keys:
        av, bv = float(a.get(k, 0.0)), float(b.get(k, 0.0))
        scale = max(abs(av), abs(bv), 1.0)
        if abs(av - bv) > _DEDUPE_RTOL * scale:
            return False
    return True


def add(
    vector: Dict[str, float],
    *,
    reason: str,
    trust: Optional[Dict[str, Any]] = None,
    source: str = "live_query",
) -> Optional[Dict[str, Any]]:
    """Append a low-trust input vector. Returns the stored entry, or None
    if it de-duped against an existing open entry or the cap was hit."""
    with _LOCK:
        entries = _load()
        open_entries = [e for e in entries if e.get("status") == "open"]
        for e in open_entries:
            if _same_point(e.get("vector", {}), vector):
                e["seen_count"] = int(e.get("seen_count", 1)) + 1
                e["last_seen_at"] = _now()
                _save(entries)
                return None
        if len(open_entries) >= _MAX_OPEN:
            return None
        entry = {
            "id": f"pend_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}",
            "created_at": _now(),
            "last_seen_at": _now(),
            "seen_count": 1,
            "status": "open",
            "source": source,
            "reason": reason,
            "trust": trust or {},
            "vector": {k: float(v) for k, v in vector.items()},
        }
        entries.append(entry)
        _save(entries)
        return entry


def list_entries(status: Optional[str] = "open") -> List[Dict[str, Any]]:
    entries = _load()
    if status:
        entries = [e for e in entries if e.get("status") == status]
    entries.sort(key=lambda e: e.get("created_at", ""), reverse=True)
    return entries


def set_status(entry_id: str, status: str) -> bool:
    with _LOCK:
        entries = _load()
        for e in entries:
            if e.get("id") == entry_id:
                e["status"] = status
                e["updated_at"] = _now()
                _save(entries)
                return True
        return False


def mark_batched(entry_ids: List[str], round_id: str) -> None:
    with _LOCK:
        entries = _load()
        wanted = set(entry_ids)
        for e in entries:
            if e.get("id") in wanted:
                e["status"] = "batched"
                e["round_id"] = round_id
                e["updated_at"] = _now()
        _save(entries)
