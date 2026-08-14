"""Runnable Kubernetes worker entrypoint for the transactional outbox."""
from __future__ import annotations

import asyncio
import contextlib
import os
from dataclasses import dataclass

import uvicorn
from fastapi import FastAPI, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .outbox import OutboxWorker
from .outbox_delivery import WebhookDeliveryClient
from .repositories import PostgresEnterpriseRepository
from .settings import get_settings


@dataclass
class WorkerState:
    ready: bool = False
    shutting_down: bool = False


def create_health_app(state: WorkerState) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None)

    @app.get("/health/live", include_in_schema=False)
    async def live() -> dict[str, str]:
        return {"status": "shutting_down" if state.shutting_down else "ok"}

    @app.get("/health/ready", include_in_schema=False)
    async def ready() -> dict[str, str]:
        if state.ready and not state.shutting_down:
            return {"status": "ready"}
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="worker dependencies unavailable")

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


async def run_worker_loop(worker: OutboxWorker, repository: PostgresEnterpriseRepository, state: WorkerState, worker_id: str, poll: float) -> None:
    while not state.shutting_down:
        try:
            processed = await worker.process_once(worker_id)
            state.ready = await repository.ready()
            if processed == 0:
                await asyncio.sleep(poll)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Keep the process alive for liveness; readiness prevents new traffic/false health.
            # Logging integration must record only stable error codes, never event payloads.
            state.ready = False
            await asyncio.sleep(min(max(poll, 1.0), 10.0))


async def serve() -> None:
    settings = get_settings()
    settings.assert_worker_safe()
    database_url = settings.outbox_worker_database_url
    if not database_url:
        raise RuntimeError("DATASENSE_OUTBOX_WORKER_DATABASE_URL is required")
    token = settings.required_secret("Outbox webhook token", settings.outbox_webhook_token_file)
    if not settings.outbox_webhook_url:
        raise RuntimeError("DATASENSE_OUTBOX_WEBHOOK_URL is required")

    repository = PostgresEnterpriseRepository(database_url)
    await repository.open()
    state = WorkerState()
    worker = OutboxWorker(
        repository,
        WebhookDeliveryClient(settings.outbox_webhook_url, token),
        batch_size=settings.outbox_batch_size,
        lease_seconds=settings.outbox_lease_seconds,
        max_attempts=settings.outbox_max_attempts,
    )
    worker_id = os.environ.get("WORKER_IDENTITY", "datasense-outbox-worker")
    worker_task = asyncio.create_task(
        run_worker_loop(worker, repository, state, worker_id, settings.outbox_poll_interval_seconds)
    )
    server = uvicorn.Server(uvicorn.Config(
        create_health_app(state), host="0.0.0.0", port=int(os.environ.get("WORKER_METRICS_PORT", "9090")),
        log_level=settings.log_level.lower(), access_log=False,
    ))
    try:
        await server.serve()
    finally:
        state.shutting_down = True
        worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task
        await repository.close()


if __name__ == "__main__":  # pragma: no cover - deployment entrypoint
    asyncio.run(serve())
