"""Immutable runtime evidence and optional integrity-checked JSONL persistence."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class RuntimeEvent:
    """JSON payload avoids mutable nested objects escaping the snapshot."""

    sequence: int
    event_id: str
    task_id: str
    timestamp: str
    kind: str
    payload_json: str
    previous_hash: str
    digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "event_id": self.event_id,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "kind": self.kind,
            "payload": json.loads(self.payload_json),
            "previous_hash": self.previous_hash,
            "digest": self.digest,
        }


def _digest(row: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


class EventJournal:
    """Single writer per task/file. Persist before publishing; fail on sink errors.

    Hash chaining detects corruption within retained records, not removal of a
    complete suffix or malicious rewriting by a file owner.
    Restore is evidence recovery, never authorization to resume an old task.
    """

    def __init__(self, task_id: str, path: Path | None = None) -> None:
        if not task_id:
            raise ValueError("task_id must not be empty")
        self.task_id = task_id
        self.path = path
        self._lock = threading.RLock()
        self._events: list[RuntimeEvent] = []
        if path is not None and path.exists():
            for line in path.read_text().splitlines():
                row = json.loads(line)
                digest = row.pop("digest")
                expected_previous = self._events[-1].digest if self._events else ""
                if (
                    row["task_id"] != task_id
                    or row["sequence"] != len(self._events) + 1
                    or row["previous_hash"] != expected_previous
                    or digest != _digest(row)
                ):
                    raise ValueError("Invalid audit chain or task identity")
                self._events.append(
                    RuntimeEvent(
                        payload_json=json.dumps(row.pop("payload"), allow_nan=False),
                        digest=digest,
                        **row,
                    )
                )

    def append(self, kind: str, payload: dict[str, Any]) -> RuntimeEvent:
        with self._lock:
            # Canonical serialization validates and copies before touching durable state.
            copied = json.loads(json.dumps(payload, allow_nan=False))
            row = {
                "sequence": len(self._events) + 1,
                "event_id": str(uuid4()),
                "task_id": self.task_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "kind": kind,
                "payload": copied,
                "previous_hash": self._events[-1].digest if self._events else "",
            }
            digest = _digest(row)
            event = RuntimeEvent(
                sequence=row["sequence"],
                event_id=row["event_id"],
                task_id=self.task_id,
                timestamp=row["timestamp"],
                kind=kind,
                payload_json=json.dumps(copied, allow_nan=False),
                previous_hash=row["previous_hash"],
                digest=digest,
            )
            if self.path is not None:
                fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
                with os.fdopen(fd, "a") as stream:
                    stream.write(json.dumps(event.to_dict(), allow_nan=False) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            self._events.append(event)
            return event

    def export(self, after: int = 0) -> list[dict[str, Any]]:
        if after < 0:
            raise ValueError("after must be nonnegative")
        with self._lock:
            return [event.to_dict() for event in self._events if event.sequence > after]
