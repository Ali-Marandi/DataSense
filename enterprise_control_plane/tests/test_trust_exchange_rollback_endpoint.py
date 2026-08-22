from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from enterprise_control_plane.app.action_gate_rollback import (
    ExecutionMode,
    MemoryRollbackRepository,
    RolloutMode,
    RolloutState,
    TrustExchangeRollbackIngress,
)
from enterprise_control_plane.app.auth import AuthorizationCodeService, TokenService
from enterprise_control_plane.app.ephemeral_store import InMemoryEphemeralStore
from enterprise_control_plane.app.main import ControlPlaneComponents, create_app
from enterprise_control_plane.app.rbac import InMemoryAuditSink, PermissionService
from enterprise_control_plane.app.trust_exchange import (
    Ed25519KeyRecord,
    KeyStatus,
    MemoryTrustRegistry,
    TrustRelationship,
    build_jws_receipt,
    new_test_private_key,
    public_key_bytes,
    valid_test_payload,
)


NOW = datetime.now(timezone.utc).replace(microsecond=0)
ORG_ID = "00000000-0000-0000-0000-000000000001"
SCOPE = "action.external"


def _tokens() -> TokenService:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = private_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    public = private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    return TokenService("https://control.test", "datasense-desktop", private, public, 600)


def _state() -> RolloutState:
    return RolloutState(
        organization_id=ORG_ID,
        scope=SCOPE,
        mode=RolloutMode.ENFORCE,
        execution_mode=ExecutionMode.ALLOW_GUARDED,
        active_policy_digest="sha256:" + "a" * 64,
        last_known_good_policy_digest="sha256:" + "b" * 64,
        version=1,
        gate_epoch=1,
    )


def _ingress():
    private_key = new_test_private_key()
    relationship = TrustRelationship(
        relationship_id="relationship-synthetic-1",
        issuer="urn:datasense:issuer:synthetic",
        receiver_organization_id=ORG_ID,
        environment="staging",
        allowed_action_types=frozenset({"rollback.trigger"}),
    )
    registry = MemoryTrustRegistry([relationship], [Ed25519KeyRecord(
        issuer=relationship.issuer,
        key_id="issuer-key-v1",
        public_key=public_key_bytes(private_key),
        status=KeyStatus.ACTIVE,
        not_before=NOW - timedelta(days=1),
        not_after=NOW + timedelta(days=1),
        environment="staging",
    )])
    store = InMemoryEphemeralStore()
    ingress = TrustExchangeRollbackIngress(
        repository=MemoryRollbackRepository([_state()]),
        registry_factory=lambda _organization_id: registry,
        replay_store=store,
        receiver_organization_id=ORG_ID,
        environment="staging",
        allowed_scopes=frozenset({SCOPE}),
    )
    payload = valid_test_payload(now=NOW, relationship=relationship)
    payload["nonce"] = "endpoint-nonce-001"
    envelope = build_jws_receipt(private_key=private_key, key_id="issuer-key-v1", payload=payload)
    return ingress, envelope


def _app(ingress):
    tokens = _tokens()
    sink = InMemoryAuditSink()
    return create_app(ControlPlaneComponents(
        saml=object(),
        authorization_codes=AuthorizationCodeService(InMemoryEphemeralStore(), tokens, 90),
        token_service=tokens,
        permission_service=PermissionService(sink),
        audit_sink=sink,
        trust_exchange_rollback_ingress=ingress,
    ))


def test_signed_exchange_trigger_reaches_cas_endpoint_once_and_replay_is_denied():
    ingress, envelope = _ingress()
    with TestClient(_app(ingress)) as client:
        accepted = client.post(f"/internal/v1/trust-exchange/rollback/{SCOPE}", json=envelope)
        replayed = client.post(f"/internal/v1/trust-exchange/rollback/{SCOPE}", json=envelope)

    assert accepted.status_code == 202
    assert accepted.json()["outcome"] == "rollback_active"
    assert accepted.json()["gate_epoch"] == 2
    assert replayed.status_code == 401
    assert replayed.json() == {"detail": "trust exchange trigger denied"}


def test_exchange_trigger_for_scope_outside_allowlist_is_denied_without_state_leakage():
    ingress, envelope = _ingress()
    with TestClient(_app(ingress)) as client:
        response = client.post("/internal/v1/trust-exchange/rollback/not-allowed.scope", json=envelope)

    assert response.status_code == 401
    assert response.json() == {"detail": "trust exchange trigger denied"}
