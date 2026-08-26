from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from uuid import uuid4

_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
_WINDOWS_PATH_PATTERN = re.compile(r"\b[A-Za-z]:\\[^\s\"']+")
_POSIX_PATH_PATTERN = re.compile(r"(?<![\w-])/(?:[^\s\"']+/)+[^\s\"']*")
_MAX_TEXT_LENGTH = 1_500


def sanitize_text(value: object) -> str:
    """Redact common local identifiers before they reach a local log file.

    This is a defensive fallback, not permission to log raw datasets. Services must
    still log counts, identifiers and error categories instead of cell values.
    """

    text = str(value)
    text = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    text = _WINDOWS_PATH_PATTERN.sub("[REDACTED_PATH]", text)
    text = _POSIX_PATH_PATTERN.sub("[REDACTED_PATH]", text)
    return text[:_MAX_TEXT_LENGTH]


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "schema": "datasense.log/v1",
            "at": datetime.fromtimestamp(record.created, timezone.utc).replace(microsecond=0).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize_text(record.getMessage()),
        }
        if record.exc_info:
            payload["exception"] = sanitize_text(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)


@dataclass(frozen=True)
class ErrorRecord:
    error_id: str
    at: str
    component: str
    error_type: str
    message: str
    context: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "datasense.error/v1",
            "error_id": self.error_id,
            "at": self.at,
            "component": self.component,
            "error_type": self.error_type,
            "message": self.message,
            "context": self.context,
        }


class LocalErrorMonitor:
    """Records redacted diagnostic events locally; it never uploads crash data."""

    def __init__(self, error_path: Path, logger: logging.Logger) -> None:
        self.error_path = Path(error_path)
        self.error_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logger

    def record_exception(self, exc: BaseException, *, component: str, context: dict[str, object] | None = None) -> ErrorRecord:
        safe_context = {str(key): sanitize_text(value) for key, value in (context or {}).items()}
        record = ErrorRecord(
            error_id=str(uuid4()),
            at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            component=sanitize_text(component),
            error_type=type(exc).__name__,
            message=sanitize_text(exc),
            context=safe_context,
        )
        with self.error_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.logger.error("Unhandled operation error id=%s component=%s type=%s", record.error_id, record.component, record.error_type, exc_info=exc)
        return record

    def install_global_handlers(self) -> None:
        previous_sys_hook = sys.excepthook

        def sys_hook(error_type: type[BaseException], value: BaseException, traceback_object: object) -> None:
            if issubclass(error_type, KeyboardInterrupt):
                previous_sys_hook(error_type, value, traceback_object)
                return
            self.record_exception(value, component="runtime.sys_excepthook")

        sys.excepthook = sys_hook
        if hasattr(threading, "excepthook"):
            previous_thread_hook = threading.excepthook

            def thread_hook(args: threading.ExceptHookArgs) -> None:
                if issubclass(args.exc_type, KeyboardInterrupt):
                    previous_thread_hook(args)
                    return
                self.record_exception(args.exc_value, component=f"runtime.thread:{args.thread.name}")

            threading.excepthook = thread_hook


@dataclass(frozen=True)
class Observability:
    logger: logging.Logger
    error_monitor: LocalErrorMonitor
    log_path: Path


def configure_observability(base_dir: Path, *, level: int = logging.INFO) -> Observability:
    log_dir = Path(base_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "datasense.jsonl"
    logger = logging.getLogger("datasense")
    logger.setLevel(level)
    logger.propagate = False
    for handler in list(logger.handlers):
        if getattr(handler, "_datasense_handler", False):
            logger.removeHandler(handler)
            handler.close()
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    handler._datasense_handler = True  # type: ignore[attr-defined]
    handler.setFormatter(JsonLineFormatter())
    logger.addHandler(handler)
    return Observability(
        logger=logger,
        error_monitor=LocalErrorMonitor(log_dir / "errors.jsonl", logger),
        log_path=log_path,
    )
