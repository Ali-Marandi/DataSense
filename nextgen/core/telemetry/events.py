from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

_ALLOWED_FIELDS = {
    "onboarding_completed": {"duration_bucket", "step_count", "app_version"},
    "quality_check_finished": {"rule_count_bucket", "outcome", "app_version"},
    "verified_export_finished": {"artifact_type", "outcome", "duration_bucket", "app_version"},
    "project_saved": {"duration_bucket", "outcome", "app_version"},
}
_MAX_STRING_VALUE_LENGTH = 80


@dataclass(frozen=True)
class TelemetryEvent:
    name: str
    data: dict[str, Any]

    def redacted(self, *, at: datetime | None = None, event_id: str | None = None) -> dict[str, Any]:
        allowed = _ALLOWED_FIELDS.get(self.name)
        if allowed is None:
            raise ValueError(f"Unsupported telemetry event: {self.name}")
        return {
            "schema": "datasense.telemetry/v1",
            "event_id": event_id or str(uuid4()),
            "name": self.name,
            "at": (at or datetime.now(timezone.utc)).replace(microsecond=0).isoformat(),
            "data": {key: self._safe_value(value) for key, value in self.data.items() if key in allowed},
        }

    @staticmethod
    def _safe_value(value: Any) -> str | int | float | bool | None:
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return value[:_MAX_STRING_VALUE_LENGTH]
        # Complex values can carry sensitive structures; record only their type.
        return type(value).__name__


@dataclass(frozen=True)
class TelemetryBatch:
    events: tuple[dict[str, Any], ...]

    @property
    def count(self) -> int:
        return len(self.events)


class TelemetryQueue:
    """Privacy-preserving local JSONL queue.

    This class never sends data over the network. A future uploader must request an
    explicit user consent signal and consume `read_batch` rather than reading queue
    files directly.
    """

    def __init__(self, path: Path, *, max_events: int = 1_000, max_bytes: int = 1_000_000) -> None:
        if max_events < 1 or max_bytes < 1:
            raise ValueError("Telemetry retention limits must be positive.")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_events = max_events
        self.max_bytes = max_bytes

    def enqueue(self, event: TelemetryEvent, consent: bool) -> bool:
        if not consent:
            return False
        serialized = json.dumps(event.redacted(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(serialized + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.prune()
        return True

    def read_batch(self, limit: int = 100) -> TelemetryBatch:
        if limit < 1:
            raise ValueError("Telemetry batch limit must be positive.")
        return TelemetryBatch(tuple(self._read_events()[:limit]))

    def acknowledge(self, event_ids: set[str]) -> int:
        if not event_ids:
            return 0
        events = self._read_events()
        remaining = [event for event in events if event.get("event_id") not in event_ids]
        removed = len(events) - len(remaining)
        if removed:
            self._atomic_replace(remaining)
        return removed

    def prune(self) -> int:
        events = self._read_events()
        kept = events[-self.max_events :]
        while kept and len(self._serialize_events(kept).encode("utf-8")) > self.max_bytes:
            kept.pop(0)
        removed = len(events) - len(kept)
        if removed:
            self._atomic_replace(kept)
        return removed

    def _read_events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if self._is_valid_event(event):
                events.append(event)
        return events

    @staticmethod
    def _is_valid_event(event: Any) -> bool:
        return isinstance(event, dict) and event.get("schema") == "datasense.telemetry/v1" and isinstance(event.get("event_id"), str)

    @staticmethod
    def _serialize_events(events: list[dict[str, Any]]) -> str:
        return "".join(json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for event in events)

    def _atomic_replace(self, events: list[dict[str, Any]]) -> None:
        content = self._serialize_events(events)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, delete=False, suffix=".tmp") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, self.path)
