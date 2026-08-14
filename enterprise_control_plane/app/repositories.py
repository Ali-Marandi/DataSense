"""PostgreSQL adapters for tenant configuration, membership resolution and audit evidence."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .models import AuditEvent, SamlConnection
from .outbox import OutboxEvent, OutboxStats
from .quality_gate import QualityGateObservation
from .saml import ResolvedIdentity


class PostgresEnterpriseRepository:
    def __init__(self, database_url: str) -> None:
        try:
            from psycopg_pool import AsyncConnectionPool
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("psycopg[pool] is required for PostgreSQL repositories") from exc
        # SQLAlchemy URLs are convenient elsewhere but psycopg expects the PostgreSQL scheme.
        self.pool = AsyncConnectionPool(database_url.replace("postgresql+psycopg://", "postgresql://"), open=False)

    async def open(self) -> None:
        await self.pool.open(wait=True)

    async def close(self) -> None:
        await self.pool.close()

    async def ready(self) -> bool:
        """Return false rather than leaking backend errors through a readiness probe."""
        try:
            async with self.pool.connection() as conn, conn.cursor() as cursor:
                await cursor.execute("SELECT 1")
                await cursor.fetchone()
            return True
        except Exception:
            return False

    async def get_enabled_by_slug(self, slug: str) -> SamlConnection | None:
        query = """
          SELECT o.id::text AS organization_id, o.slug, sc.idp_entity_id, sc.idp_sso_url,
                 sc.idp_x509_cert_pem, sc.sp_entity_id, sc.acs_url, sc.attribute_mapping
          FROM organizations o JOIN saml_connections sc ON sc.organization_id = o.id
          WHERE o.slug = %s AND o.status = 'active' AND sc.enabled = true
        """
        async with self.pool.connection() as conn, conn.cursor() as cursor:
            await cursor.execute(query, (slug,))
            row = await cursor.fetchone()
        if row is None:
            return None
        return SamlConnection(
            organization_id=str(row[0]), slug=row[1], idp_entity_id=row[2], idp_sso_url=row[3],
            idp_x509_cert_pem=row[4], sp_entity_id=row[5], acs_url=row[6], attribute_mapping=row[7] or {},
        )

    async def resolve(self, connection: SamlConnection, external_subject: str, attributes: dict[str, list[str]]) -> ResolvedIdentity | None:
        # The database, not mutable IdP role attributes, is the authorization source of truth.
        query = """
          SELECT i.id::text, m.id::text, i.email,
            COALESCE(array_remove(array_agg(DISTINCT r.name), NULL), ARRAY[]::text[]) AS roles,
            COALESCE(array_remove(array_agg(DISTINCT rp.permission_code), NULL), ARRAY[]::text[]) AS permissions
          FROM identities i
          JOIN memberships m ON m.identity_id = i.id
          LEFT JOIN membership_roles mr ON mr.membership_id = m.id
          LEFT JOIN roles r ON r.id = mr.role_id
          LEFT JOIN role_permissions rp ON rp.role_id = r.id
          WHERE i.issuer = %s AND i.external_subject = %s
            AND m.organization_id = %s::uuid AND m.status = 'active'
          GROUP BY i.id, m.id, i.email
        """
        async with self.pool.connection() as conn, conn.cursor() as cursor:
            await cursor.execute(query, (connection.idp_entity_id, external_subject, connection.organization_id))
            row = await cursor.fetchone()
        if row is None:
            return None
        return ResolvedIdentity(
            subject=str(row[0]), organization_id=connection.organization_id, membership_id=str(row[1]),
            roles=tuple(row[3]), permissions=tuple(row[4]), email=row[2],
        )

    async def write(self, event: AuditEvent) -> None:
        query = """
          INSERT INTO audit_events (organization_id, action, outcome, resource_type, resource_id_hash,
                                    correlation_id, occurred_at, details)
          VALUES (NULLIF(%s, 'unknown')::uuid, %s, %s, %s, %s, %s::uuid, %s::timestamptz, %s::jsonb)
        """
        import json
        async with self.pool.connection() as conn, conn.cursor() as cursor:
            await cursor.execute(query, (
                event.organization_id, event.action, event.outcome, event.resource_type,
                event.resource_id, event.correlation_id, event.occurred_at, json.dumps(event.details),
            ))
            await conn.commit()

    async def record_quality_gate_observation(
        self,
        *,
        organization_id: str,
        actor_subject: str,
        observation: QualityGateObservation,
    ) -> bool:
        """Persist evidence/audit/outbox as one tenant-scoped, idempotent transaction."""
        observation_query = """
          INSERT INTO quality_gate_observations (
            organization_id, execution_id, contract_fingerprint, policy_tier, decision, score,
            critical_failures, high_failures, rule_errors, rows_examined, actor_subject
          ) VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
          ON CONFLICT (organization_id, execution_id) DO NOTHING
          RETURNING id
        """
        audit_query = """
          INSERT INTO audit_events (organization_id, action, outcome, correlation_id, details)
          VALUES (%s::uuid, 'quality_gate.observe', 'success', gen_random_uuid(), %s::jsonb)
        """
        outbox_query = """
          INSERT INTO outbox_events (organization_id, event_type, payload, idempotency_key)
          VALUES (%s::uuid, 'quality_gate.blocked', %s::jsonb, %s)
          ON CONFLICT (organization_id, idempotency_key) DO NOTHING
        """
        details = {
            "execution_id": observation.execution_id,
            "contract_fingerprint": observation.contract_fingerprint,
            "decision": observation.decision,
            "policy_tier": observation.policy_tier,
            "score": observation.score,
            "critical_failures": observation.critical_failures,
            "high_failures": observation.high_failures,
            "rule_errors": observation.rule_errors,
            "rows": observation.rows,
        }
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cursor:
                    # RLS is active for the API role. Worker claims use a dedicated least-privilege
                    # queue role rather than relaxing per-tenant policies on this connection.
                    await cursor.execute("SELECT set_config('app.organization_id', %s, true)", (organization_id,))
                    await cursor.execute(observation_query, (
                        organization_id, observation.execution_id, observation.contract_fingerprint,
                        observation.policy_tier, observation.decision, observation.score,
                        observation.critical_failures, observation.high_failures, observation.rule_errors,
                        observation.rows, actor_subject,
                    ))
                    inserted = await cursor.fetchone()
                    if inserted is None:
                        return False
                    await cursor.execute(audit_query, (organization_id, json.dumps(details)))
                    if observation.decision == "blocked":
                        await cursor.execute(outbox_query, (
                            organization_id,
                            json.dumps({"version": 1, **details}),
                            f"quality-gate-blocked:{observation.execution_id}",
                        ))
        return True

    async def enqueue_outbox_event(
        self,
        *,
        organization_id: str,
        event_type: str,
        payload: dict[str, object],
        idempotency_key: str,
    ) -> bool:
        """Insert a metadata-only event exactly once per tenant/idempotency key."""
        query = """
          INSERT INTO outbox_events (organization_id, event_type, payload, idempotency_key)
          VALUES (%s::uuid, %s, %s::jsonb, %s)
          ON CONFLICT (organization_id, idempotency_key) DO NOTHING
        """
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT set_config('app.organization_id', %s, true)", (organization_id,))
                    await cursor.execute(query, (organization_id, event_type, json.dumps(payload), idempotency_key))
                    inserted = cursor.rowcount == 1
        return inserted

    async def recover_stale_leases(self, *, now: datetime) -> int:
        query = """
          UPDATE outbox_events
             SET status = 'pending', lease_expires_at = NULL, lease_owner = NULL,
                 next_attempt_at = %s::timestamptz, updated_at = now()
           WHERE status = 'processing' AND lease_expires_at < %s::timestamptz
        """
        async with self.pool.connection() as conn, conn.cursor() as cursor:
            await cursor.execute(query, (now, now))
            recovered = cursor.rowcount
            await conn.commit()
        return recovered

    async def claim(self, *, worker_id: str, limit: int, lease_until: datetime) -> list[OutboxEvent]:
        # FOR UPDATE SKIP LOCKED lets multiple workers make progress without double-delivery.
        query = """
          WITH candidates AS (
            SELECT id
              FROM outbox_events
             WHERE status = 'pending' AND next_attempt_at <= now()
             ORDER BY next_attempt_at, created_at
             FOR UPDATE SKIP LOCKED
             LIMIT %s
          )
          UPDATE outbox_events AS event
             SET status = 'processing', attempts = event.attempts + 1,
                 lease_owner = %s, lease_expires_at = %s::timestamptz, updated_at = now()
            FROM candidates
           WHERE event.id = candidates.id
        RETURNING event.id::text, event.organization_id::text, event.event_type, event.payload,
                  event.attempts, event.idempotency_key
        """
        async with self.pool.connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cursor:
                    await cursor.execute(query, (limit, worker_id, lease_until))
                    rows = await cursor.fetchall()
        return [OutboxEvent(str(row[0]), str(row[1]), str(row[2]), dict(row[3] or {}), int(row[4]), str(row[5])) for row in rows]

    async def mark_sent(self, event_id: str) -> None:
        await self._transition(event_id, "sent", None, None)

    async def mark_retry(self, event_id: str, *, next_attempt_at: datetime, error_code: str) -> None:
        await self._transition(event_id, "pending", error_code, next_attempt_at)

    async def mark_dead(self, event_id: str, *, error_code: str) -> None:
        await self._transition(event_id, "dead", error_code, None)

    async def _transition(
        self,
        event_id: str,
        target_status: str,
        error_code: str | None,
        next_attempt_at: datetime | None,
    ) -> None:
        query = """
          UPDATE outbox_events
             SET status = %s,
                 last_error_code = %s,
                 next_attempt_at = COALESCE(%s::timestamptz, next_attempt_at),
                 sent_at = CASE WHEN %s = 'sent' THEN now() ELSE sent_at END,
                 dead_at = CASE WHEN %s = 'dead' THEN now() ELSE dead_at END,
                 lease_owner = NULL, lease_expires_at = NULL, updated_at = now()
           WHERE id = %s::uuid AND status = 'processing'
        """
        async with self.pool.connection() as conn, conn.cursor() as cursor:
            await cursor.execute(query, (target_status, error_code, next_attempt_at, target_status, target_status, event_id))
            if cursor.rowcount != 1:
                raise RuntimeError("outbox event transition lost its processing lease")
            await conn.commit()

    async def stats(self, *, now: datetime) -> OutboxStats:
        query = """
          SELECT
            count(*) FILTER (WHERE status = 'pending'),
            count(*) FILTER (WHERE status = 'processing'),
            count(*) FILTER (WHERE status = 'dead'),
            COALESCE(EXTRACT(EPOCH FROM (%s::timestamptz - min(created_at) FILTER (WHERE status = 'pending'))), 0)
          FROM outbox_events
        """
        async with self.pool.connection() as conn, conn.cursor() as cursor:
            await cursor.execute(query, (now,))
            row = await cursor.fetchone()
        return OutboxStats(int(row[0]), int(row[1]), int(row[2]), float(row[3]))
