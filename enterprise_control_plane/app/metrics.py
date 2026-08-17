"""Prometheus metrics with privacy-safe, low-cardinality labels.

Never use organization ID, dataset ID, email, request ID, exception text, or a raw URL as a metric label.
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "datasense_control_plane_http_requests_total",
    "Completed HTTP requests handled by the Control Plane.",
    ("method", "route", "status"),
)
HTTP_DURATION_SECONDS = Histogram(
    "datasense_control_plane_http_request_duration_seconds",
    "HTTP request duration for the Control Plane.",
    ("method", "route"),
)
AUTH_DECISIONS = Counter(
    "datasense_control_plane_authorization_decisions_total",
    "Authorization outcomes without tenant or resource identifiers.",
    ("outcome", "permission"),
)
SAML_VALIDATIONS = Counter(
    "datasense_control_plane_saml_validations_total",
    "SAML ACS validation outcomes without assertion content.",
    ("outcome",),
)
QUALITY_GATE_DECISIONS = Counter(
    "datasense_quality_gate_decisions_total",
    "Quality Gate decisions emitted by the Control Plane.",
    ("decision", "policy_tier"),
)
OUTBOX_DELIVERIES = Counter(
    "datasense_outbox_delivery_attempts_total",
    "Outbox delivery attempts classified by outcome.",
    ("event_type", "outcome"),
)
OUTBOX_PENDING = Gauge(
    "datasense_outbox_pending_events",
    "Current outbox events waiting to be processed.",
)
OUTBOX_OLDEST_PENDING_SECONDS = Gauge(
    "datasense_outbox_oldest_pending_age_seconds",
    "Age in seconds of the oldest pending outbox event, or zero when empty.",
)
OUTBOX_PROCESSING_LEASES = Gauge(
    "datasense_outbox_processing_leases",
    "Outbox events currently owned by a worker lease.",
)
OUTBOX_DEAD = Gauge(
    "datasense_outbox_dead_events",
    "Outbox events in the dead-letter state.",
)
OUTBOX_LEASE_RECOVERIES = Counter(
    "datasense_outbox_lease_recoveries_total",
    "Outbox events returned to pending after a stale worker lease.",
)
ACTIVATION_SUPPRESSIONS = Counter(
    "datasense_activation_suppressions_total",
    "Fail-closed activation decisions without tenant, recipient, or payload labels.",
    ("reason_code",),
)
ACTIVATION_PAYLOAD_REJECTIONS = Counter(
    "datasense_activation_payload_rejections_total",
    "Rejected activation payloads classified by a bounded reason code.",
    ("reason_code",),
)
ACTIVATION_ALERTS = Counter(
    "datasense_activation_controller_alerts_total",
    "Signed controller alerts classified by a bounded verification outcome.",
    ("outcome",),
)
