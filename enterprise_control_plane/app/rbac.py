"""RBAC enforcement. Authentication is middleware; authorization is explicit per route."""
from __future__ import annotations

import hashlib
import hmac
from typing import Awaitable, Callable, Protocol
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from .models import AuditEvent, Permission, Principal, ResourceRef


class TokenVerifier(Protocol):
    def verify_access_token(self, token: str) -> Principal: ...


class AuditSink(Protocol):
    async def write(self, event: AuditEvent) -> None: ...


class InMemoryAuditSink:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def write(self, event: AuditEvent) -> None:
        self.events.append(event)


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    return token if scheme.lower() == "bearer" and token else None


class PermissionMiddleware(BaseHTTPMiddleware):
    """Validates a bearer token and attaches a Principal without authorizing any action."""

    def __init__(self, app, token_verifier: TokenVerifier, audit_sink: AuditSink) -> None:
        super().__init__(app)
        self.token_verifier = token_verifier
        self.audit_sink = audit_sink

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request.state.correlation_id = request.headers.get("X-Request-ID", str(uuid4()))
        token = _bearer_token(request.headers.get("Authorization"))
        request.state.principal = None
        if token:
            try:
                request.state.principal = self.token_verifier.verify_access_token(token)
            except Exception:
                # Avoid details that let an attacker distinguish expiry, signature, or audience errors.
                await self.audit_sink.write(AuditEvent(
                    organization_id="unknown", actor_subject=None, action="token.validate",
                    outcome="denied", correlation_id=request.state.correlation_id,
                ))
                return JSONResponse({"detail": "invalid authentication credentials"}, status_code=status.HTTP_401_UNAUTHORIZED)
        return await call_next(request)


def current_principal(request: Request) -> Principal:
    principal: Principal | None = getattr(request.state, "principal", None)
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    return principal


class PermissionService:
    def __init__(self, audit_sink: AuditSink) -> None:
        self.audit_sink = audit_sink

    async def check_permission(self, principal: Principal, permission: Permission, resource: ResourceRef, correlation_id: str) -> None:
        tenant_match = hmac.compare_digest(principal.organization_id, resource.organization_id)
        allowed = tenant_match and principal.can(permission)
        await self.audit_sink.write(AuditEvent(
            organization_id=principal.organization_id,
            actor_subject=principal.subject,
            action=f"authorize:{permission.value}",
            outcome="allowed" if allowed else "denied",
            resource_type=resource.resource_type,
            resource_id=resource.resource_id,
            correlation_id=correlation_id,
            details={"tenant_match": tenant_match, "roles": list(principal.roles)},
        ))
        if not tenant_match:
            # 404 protects cross-tenant resource enumeration.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")

    async def tenant_boundary_check(self, principal: Principal, organization_id: str, correlation_id: str) -> None:
        resource = ResourceRef(resource_type="organization", resource_id=organization_id, organization_id=organization_id)
        await self.check_permission(principal, Permission.PROJECT_READ, resource, correlation_id)


def require_permission(
    permission: Permission,
    resource_resolver: Callable[[Request, Principal], Awaitable[ResourceRef]],
    service: PermissionService,
):
    """FastAPI dependency factory. Resolver must obtain a resource scoped by organization_id."""
    async def enforce(request: Request, principal: Principal = Depends(current_principal)) -> Principal:
        resource = await resource_resolver(request, principal)
        await service.check_permission(principal, permission, resource, request.state.correlation_id)
        return principal
    return enforce


def stable_resource_hash(resource_id: str, audit_hmac_key: bytes) -> str:
    """Optional non-reversible identifier for privacy-preserving audit exports."""
    return hmac.new(audit_hmac_key, resource_id.encode("utf-8"), hashlib.sha256).hexdigest()
