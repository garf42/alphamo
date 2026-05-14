"""Append-only audit trail of meta-layer decisions.

The drift log is load-bearing: every curator decision is logged with
timestamp, trigger, classification, action, and rationale. Without it, two
runs of the same input could diverge and there'd be no way to tell whether
divergence was legitimate (meta caught something real) or pathological
(meta drifted). JSONL on disk — append-only by construction.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """One row in the drift log.

    `run_id` ties each event to the specific Run row in the DB so the harvest
    can filter the drift log down to a single run.
    """

    timestamp: str
    run_id: str
    trigger: str
    classification: str
    action: str
    rationale: str
    payload: dict[str, Any] = Field(default_factory=dict)


class AuditLog:
    """JSONL audit log. Open per-write, never truncate."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: AuditEvent) -> None:
        with self.path.open("a") as f:
            f.write(event.model_dump_json() + "\n")

    def read_all(self) -> list[AuditEvent]:
        if not self.path.exists():
            return []
        events: list[AuditEvent] = []
        with self.path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(AuditEvent.model_validate_json(line))
        return events

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()
