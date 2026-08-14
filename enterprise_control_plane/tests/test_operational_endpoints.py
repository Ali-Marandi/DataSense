from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from enterprise_control_plane.app.auth import AuthorizationCodeService, TokenService
from enterprise_control_plane.app.ephemeral_store import InMemoryEphemeralStore
from enterprise_control_plane.app.main import ControlPlaneComponents, create_app
from enterprise_control_plane.app.rbac import InMemoryAuditSink, PermissionService


def _tokens() -> TokenService:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return TokenService("https://control.test", "datasense-desktop", private, public, 600)


def _app(ready_check):
    tokens = _tokens()
    sink = InMemoryAuditSink()
    return create_app(ControlPlaneComponents(
        saml=object(),
        authorization_codes=AuthorizationCodeService(InMemoryEphemeralStore(), tokens, 90),
        token_service=tokens,
        permission_service=PermissionService(sink),
        audit_sink=sink,
        ready_check=ready_check,
    ))


def test_health_and_metrics_endpoints_are_available_without_a_tenant_token():
    async def ready() -> bool:
        return True

    with TestClient(_app(ready)) as client:
        assert client.get("/health/live").json() == {"status": "ok"}
        assert client.get("/health/ready").json() == {"status": "ready"}
        metrics = client.get("/metrics")

    assert metrics.status_code == 200
    assert "datasense_control_plane_http_requests_total" in metrics.text
    # Route template, not raw path or tenant/resource identity, is the metric label contract.
    assert 'route="/health/live"' in metrics.text


def test_readiness_returns_503_when_a_dependency_check_fails():
    async def not_ready() -> bool:
        return False

    with TestClient(_app(not_ready)) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "dependencies unavailable"}
