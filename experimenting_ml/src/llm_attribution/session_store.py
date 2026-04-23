"""
Persistent session: thread id + last structured snapshot + conversation turns.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from llm_attribution.schema import AttributionSnapshot


@dataclass
class SessionRecord:
    thread_id: str
    target: Optional[str] = None
    last_snapshot: Optional[Dict[str, Any]] = None
    turns: List[Dict[str, str]] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @staticmethod
    def from_json(s: str) -> "SessionRecord":
        raw = json.loads(s)
        return SessionRecord(
            thread_id=raw["thread_id"],
            target=raw.get("target"),
            last_snapshot=raw.get("last_snapshot"),
            turns=list(raw.get("turns") or []),
        )


class FileSessionStore:
    """One JSON file per thread under ``base_dir``."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, thread_id: str) -> Path:
        safe = thread_id.replace("/", "_")
        return self.base_dir / f"{safe}.json"

    def load(self, thread_id: str) -> Optional[SessionRecord]:
        p = self._path(thread_id)
        if not p.is_file():
            return None
        return SessionRecord.from_json(p.read_text(encoding="utf-8"))

    def save(self, record: SessionRecord) -> None:
        p = self._path(record.thread_id)
        p.write_text(record.to_json(), encoding="utf-8")

    def new_thread_id(self) -> str:
        return str(uuid.uuid4())

    def append_turn(
        self,
        thread_id: str,
        *,
        user: str,
        assistant: str,
        snapshot: Optional[AttributionSnapshot] = None,
        target: Optional[str] = None,
    ) -> SessionRecord:
        rec = self.load(thread_id) or SessionRecord(thread_id=thread_id)
        if target:
            rec.target = target
        if snapshot is not None:
            rec.last_snapshot = snapshot.model_dump()
        rec.turns.append({"user": user, "assistant": assistant})
        self.save(rec)
        return rec
