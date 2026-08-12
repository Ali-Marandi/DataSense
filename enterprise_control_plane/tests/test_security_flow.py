from __future__ import annotations

import asyncio
import base64
import hashlib
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from enterprise_control_plane.app.auth import AuthorizationCodeService, TokenService
from enterprise_control_plane.app.ephemeral_store import InMemoryEphemeralStore
from enterprise_control_plane.app.models import Permission, Principal, ResourceRef, SamlConnection
from enterprise_control_plane.app.rbac import InMemoryAuditSink, PermissionService
from enterprise_control_plane.app.saml import ResolvedIdentity, SamlSecurityError, SamlServiceProvider


def run(coro):
    return asyncio.run(coro)


def pem_keys() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = private_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    public = private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    return private, public


def pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def test_authorization_code_requires_matching_pkce_and_is_single_use():
    private, public = pem_keys()
    tokens = TokenService("https://control.test", "datasense-desktop", private, public, 600)
    codes = AuthorizationCodeService(InMemoryEphemeralStore(), tokens, 90)
    verifier = "a" * 43
    identity = ResolvedIdentity("subject-1", "org-1", "membership-1", ("analyst",), ("project.read",), "person@example.com")

    code = run(codes.issue_code(identity, pkce_challenge(verifier), "datasense://auth/callback"))
    issued = run(codes.exchange_code(code, verifier, "datasense://auth/callback"))
    principal = tokens.verify_access_token(issued["access_token"])
    assert principal.organization_id == "org-1"
    assert principal.can(Permission.PROJECT_READ)
    with pytest.raises(ValueError, match="invalid or expired"):
        run(codes.exchange_code(code, verifier, "datasense://auth/callback"))


def test_authorization_code_rejects_wrong_pkce_verifier():
    private, public = pem_keys()
    codes = AuthorizationCodeService(InMemoryEphemeralStore(), TokenService("https://control.test", "datasense-desktop", private, public, 600), 90)
    identity = ResolvedIdentity("subject-1", "org-1", "membership-1", (), (), None)
    code = run(codes.issue_code(identity, pkce_challenge("a" * 43), "datasense://auth/callback"))
    with pytest.raises(ValueError, match="PKCE"):
        run(codes.exchange_code(code, "b" * 43, "datasense://auth/callback"))


def test_permission_service_hides_cross_tenant_resource_and_audits_denial():
    sink = InMemoryAuditSink()
    service = PermissionService(sink)
    principal = Principal("subject-1", "org-1", "membership-1", frozenset({Permission.PROJECT_READ}))
    foreign_dataset = ResourceRef("dataset", "dataset-7", "org-2")
    with pytest.raises(Exception) as failure:
        run(service.check_permission(principal, Permission.PROJECT_READ, foreign_dataset, "req-1"))
    assert getattr(failure.value, "status_code") == 404
    assert sink.events[-1].outcome == "denied"
    assert sink.events[-1].details["tenant_match"] is False


class FakeConnectionRepository:
    connection = SamlConnection(
        organization_id="org-1", slug="acme", idp_entity_id="https://idp.test/metadata",
        idp_sso_url="https://idp.test/sso", idp_x509_cert_pem="test-cert",
        sp_entity_id="https://control.test/saml/acme", acs_url="https://control.test/v1/auth/saml/acme/acs",
    )

    async def get_enabled_by_slug(self, slug: str):
        return self.connection if slug == "acme" else None


class FakeIdentityResolver:
    async def resolve(self, connection, external_subject, attributes):
        return ResolvedIdentity(external_subject, connection.organization_id, "membership-1", ("analyst",), ("project.read",), "person@example.com")


def test_saml_acs_uses_strict_toolkit_configuration_and_rejects_assertion_replay(monkeypatch):
    import onelogin.saml2.auth

    class FakeAuth:
        def __init__(self, request_data, settings):
            assert settings["strict"] is True
            assert settings["security"]["wantAssertionsSigned"] is True
            assert settings["security"]["wantMessagesSigned"] is True
            assert settings["security"]["wantAssertionsEncrypted"] is True
        def process_response(self, request_id):
            assert request_id == "request-1"
        def get_errors(self): return []
        def is_authenticated(self): return True
        def get_last_assertion_id(self): return "assertion-1"
        def get_last_message_id(self): return None
        def get_attributes(self): return {"email": ["person@example.com"]}
        def get_nameid(self): return "external-subject-1"

    monkeypatch.setattr(onelogin.saml2.auth, "OneLogin_Saml2_Auth", FakeAuth)
    store = InMemoryEphemeralStore()
    service = SamlServiceProvider(store, FakeConnectionRepository(), FakeIdentityResolver(), 300, 120, "sp-cert", "sp-key")
    transaction = {
        "request_id": "request-1", "organization_id": "org-1", "organization_slug": "acme",
        "pkce_challenge": pkce_challenge("a" * 43), "return_uri": "datasense://auth/callback",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    run(store.put("saml-transaction", "state-1", transaction, 300))
    identity, _ = run(service.process_acs("acme", {"RelayState": "state-1", "SAMLResponse": "opaque"}))
    assert identity.subject == "external-subject-1"

    run(store.put("saml-transaction", "state-2", transaction, 300))
    with pytest.raises(SamlSecurityError, match="replayed"):
        run(service.process_acs("acme", {"RelayState": "state-2", "SAMLResponse": "opaque"}))
