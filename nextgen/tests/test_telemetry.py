from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.telemetry.events import TelemetryEvent, TelemetryQueue


def test_telemetry_requires_opt_in_and_redacts_unknown_fields(tmp_path):
    queue = TelemetryQueue(tmp_path / "events.jsonl")
    event = TelemetryEvent(
        "quality_check_finished",
        {"rule_count_bucket": "1-5", "outcome": "approved", "file_name": "sensitive.csv", "raw_values": ["secret"]},
    )

    assert not queue.enqueue(event, consent=False)
    assert not queue.path.exists()
    assert queue.enqueue(event, consent=True)

    batch = queue.read_batch()
    assert batch.count == 1
    payload = batch.events[0]
    assert payload["schema"] == "datasense.telemetry/v1"
    assert payload["data"] == {"rule_count_bucket": "1-5", "outcome": "approved"}
    assert "sensitive.csv" not in queue.path.read_text(encoding="utf-8")


def test_telemetry_rejects_unsupported_events_and_normalizes_complex_values():
    with pytest.raises(ValueError, match="Unsupported telemetry event"):
        TelemetryEvent("unknown_event", {}).redacted()

    event = TelemetryEvent("project_saved", {"duration_bucket": {"too": "complex"}, "outcome": "ok"})
    payload = event.redacted(at=datetime(2026, 8, 26, tzinfo=timezone.utc), event_id="event-1")
    assert payload["event_id"] == "event-1"
    assert payload["data"]["duration_bucket"] == "dict"


def test_telemetry_prunes_and_acknowledges_only_requested_event_ids(tmp_path):
    queue = TelemetryQueue(tmp_path / "events.jsonl", max_events=2, max_bytes=10_000)
    for index in range(3):
        queue.enqueue(TelemetryEvent("project_saved", {"duration_bucket": str(index), "outcome": "ok"}), consent=True)

    batch = queue.read_batch()
    assert batch.count == 2
    removed = queue.acknowledge({batch.events[0]["event_id"]})
    assert removed == 1
    assert queue.read_batch().count == 1


def test_telemetry_skips_malformed_local_queue_lines(tmp_path):
    queue = TelemetryQueue(tmp_path / "events.jsonl")
    queue.path.write_text("not-json\n" + '{"schema":"wrong"}\n', encoding="utf-8")

    assert queue.read_batch().count == 0
