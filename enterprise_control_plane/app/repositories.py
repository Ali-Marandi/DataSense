"""PostgreSQL adapters for tenant configuration, membership resolution and audit evidence."""
from __future__ import annotations

from typing import Any

from .models import AuditEvent, SamlConnection
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
