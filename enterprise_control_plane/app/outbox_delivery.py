"""HTTP notification adapter for the outbox worker.

Providers must honour the Idempotency-Key header. Payloads remain metadata-only and are never
written to logs or metric labels by this adapter.
"""
from __future__ import annotations

import httpx

from .outbox import DeliveryResult, OutboxEvent


class WebhookDeliveryClient:
    def __init__(self, webhook_url: str, bearer_token: str, *, timeout_seconds: float = 10.0) -> None:
        if not webhook_url.startswith("https://"):
            raise ValueError("outbox webhook URL must use HTTPS")
        self.webhook_url = webhook_url
        self.bearer_token = bearer_token
        self.timeout_seconds = timeout_seconds

    async def deliver(self, event: OutboxEvent) -> DeliveryResult:
        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Idempotency-Key": event.idempotency_key,
            "X-DataSense-Event-Type": event.event_type,
            "Content-Type": "application/json",
        }
        body = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "organization_id": event.organization_id,
            "payload": event.payload,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=False) as client:
                response = await client.post(self.webhook_url, json=body, headers=headers)
        except httpx.TimeoutException:
            return DeliveryResult("retry", "webhook_timeout")
        except httpx.TransportError:
            return DeliveryResult("retry", "webhook_transport_error")

        if 200 <= response.status_code < 300 or response.status_code == 409:
            # 409 is treated as idempotent success only when the provider documents duplicate-key semantics.
            return DeliveryResult("delivered")
        if response.status_code == 429:
            return DeliveryResult("retry", "webhook_rate_limited")
        if 500 <= response.status_code < 600:
            return DeliveryResult("retry", f"webhook_http_{response.status_code}")
        return DeliveryResult("permanent_failure", f"webhook_http_{response.status_code}")
