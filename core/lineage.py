"""Privacy-preserving, project-local transformation lineage for DataSense."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .governance import SchemaSnapshot, capture_schema


@dataclass(frozen=True)
class LineageEvent:
    """One transformation observation containing schemas and metadata, never cell values."""

    sequence: int
    operation: str
    occurred_at: str
    input_schema: SchemaSnapshot | None
    output_schema: SchemaSnapshot | None
    input_rows: int | None
    output_rows: int | None
    source: str | None = None

    @property
    def input_fingerprint(self) -> str | None:
        return self.input_schema.fingerprint if self.input_schema else None

    @property
    def output_fingerprint(self) -> str | None:
        return self.output_schema.fingerprint if self.output_schema else None

    @property
    def added_columns(self) -> tuple[str, ...]:
        before = {name for name, _, _ in self.input_schema.columns} if self.input_schema else set()
        after = {name for name, _, _ in self.output_schema.columns} if self.output_schema else set()
        return tuple(sorted(after - before))

    @property
    def removed_columns(self) -> tuple[str, ...]:
        before = {name for name, _, _ in self.input_schema.columns} if self.input_schema else set()
        after = {name for name, _, _ in self.output_schema.columns} if self.output_schema else set()
        return tuple(sorted(before - after))

    @property
    def dtype_changes(self) -> tuple[str, ...]:
        before = {name: dtype for name, dtype, _ in self.input_schema.columns} if self.input_schema else {}
        after = {name: dtype for name, dtype, _ in self.output_schema.columns} if self.output_schema else {}
        return tuple(sorted(name for name in before if name in after and before[name] != after[name]))

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "operation": self.operation,
            "occurred_at": self.occurred_at,
            "source": self.source,
            "input_rows": self.input_rows,
            "output_rows": self.output_rows,
            "input_schema": self.input_schema.to_dict() if self.input_schema else None,
            "output_schema": self.output_schema.to_dict() if self.output_schema else None,
            "input_fingerprint": self.input_fingerprint,
            "output_fingerprint": self.output_fingerprint,
            "added_columns": list(self.added_columns),
            "removed_columns": list(self.removed_columns),
            "dtype_changes": list(self.dtype_changes),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "LineageEvent":
        return cls(
            sequence=int(value.get("sequence", 0)),
            operation=str(value.get("operation", "Unknown operation")),
            occurred_at=str(value.get("occurred_at", "")),
            input_schema=SchemaSnapshot.from_dict(value.get("input_schema")),
            output_schema=SchemaSnapshot.from_dict(value.get("output_schema")),
            input_rows=None if value.get("input_rows") is None else int(value["input_rows"]),
            output_rows=None if value.get("output_rows") is None else int(value["output_rows"]),
            source=value.get("source"),
        )


@dataclass
class LineageTrail:
    """Bounded chronological data provenance that is safe to persist with a project."""

    events: list[LineageEvent] = field(default_factory=list)
    max_events: int = 200

    def record(
        self,
        operation: str,
        before: pd.DataFrame | None,
        after: pd.DataFrame | None,
        *,
        source: str | None = None,
    ) -> LineageEvent:
        event = LineageEvent(
            sequence=(self.events[-1].sequence + 1) if self.events else 1,
            operation=str(operation),
            occurred_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            input_schema=capture_schema(before),
            output_schema=capture_schema(after),
            input_rows=None if before is None else int(len(before)),
            output_rows=None if after is None else int(len(after)),
            source=source,
        )
        self.events.append(event)
        self.events = self.events[-max(int(self.max_events), 1):]
        return event

    def summary(self) -> dict[str, Any]:
        latest = self.events[-1] if self.events else None
        return {
            "event_count": len(self.events),
            "latest_operation": latest.operation if latest else None,
            "latest_at": latest.occurred_at if latest else None,
            "max_events": self.max_events,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"max_events": self.max_events, "summary": self.summary(), "events": [event.to_dict() for event in self.events]}

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "LineageTrail":
        if not value:
            return cls()
        return cls(
            max_events=max(int(value.get("max_events", 200)), 1),
            events=[LineageEvent.from_dict(event) for event in value.get("events", [])],
        )
