from __future__ import annotations

import json
import logging

from app.observability import LocalErrorMonitor, configure_observability, sanitize_text


def test_sanitize_text_redacts_emails_and_common_local_paths():
    sanitized = sanitize_text("Contact ops@example.com at C:\\Users\\alice\\sensitive.csv or /home/alice/private.csv")

    assert "ops@example.com" not in sanitized
    assert "sensitive.csv" not in sanitized
    assert "private.csv" not in sanitized
    assert sanitized.count("[REDACTED_") >= 3


def test_observability_writes_redacted_structured_json_log(tmp_path):
    observability = configure_observability(tmp_path, level=logging.INFO)
    observability.logger.info("opened /home/alice/customer.csv for finance@example.com")
    for handler in observability.logger.handlers:
        handler.flush()

    payload = json.loads(observability.log_path.read_text(encoding="utf-8").strip())

    assert payload["schema"] == "datasense.log/v1"
    assert payload["level"] == "INFO"
    assert "customer.csv" not in payload["message"]
    assert "finance@example.com" not in payload["message"]


def test_error_monitor_persists_redacted_error_reference_and_logs_exception(tmp_path):
    observability = configure_observability(tmp_path, level=logging.INFO)
    monitor = LocalErrorMonitor(tmp_path / "logs" / "errors.jsonl", observability.logger)
    try:
        raise ValueError("Could not load /home/alice/secret.csv for person@example.com")
    except ValueError as exc:
        record = monitor.record_exception(exc, component="test.import", context={"source": "/tmp/customer.csv"})
    for handler in observability.logger.handlers:
        handler.flush()

    payload = json.loads((tmp_path / "logs" / "errors.jsonl").read_text(encoding="utf-8").strip())
    assert payload["schema"] == "datasense.error/v1"
    assert payload["error_id"] == record.error_id
    assert payload["component"] == "test.import"
    assert "secret.csv" not in payload["message"]
    assert "person@example.com" not in payload["message"]
    assert "customer.csv" not in payload["context"]["source"]
