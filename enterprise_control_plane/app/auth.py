"""OAuth-style authorization-code exchange for the DataSense desktop public client."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from .ephemeral_store import EphemeralStore
from .models import AuthorizationCode, Permission, Principal
from .saml import ResolvedIdentity


def _b64url_sha256(value: str) -> str:
    digest = hashlib.sha256(value.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def validate_pkce_verifier(verifier: str) -> None:
    if not (43 <= len(verifier) <= 128) or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~" for char in verifier):
        raise ValueError("invalid PKCE verifier")


class TokenService:
    def __init__(self, issuer: str, audience: str, private_key_pem: str, public_key_pem: str, access_ttl_seconds: int) -> None:
        self.issuer = issuer
        self.audience = audience
        self.private_key_pem = private_key_pem
        self.public_key_pem = public_key_pem
        self.access_ttl_seconds = access_ttl_seconds

    def issue_access_token(self, identity: ResolvedIdentity) -> str:
        now = datetime.now(timezone.utc)
        claims = {
            "iss": self.issuer,
            "aud": self.audience,
            "sub": identity.subject,
            "org": identity.organization_id,
            "mid": identity.membership_id,
            "roles": list(identity.roles),
            "perms": list(identity.permissions),
            "email": identity.email,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(seconds=self.access_ttl_seconds),
            "jti": secrets.token_urlsafe(18),
        }
        return jwt.encode(claims, self.private_key_pem, algorithm="RS256")

    def verify_access_token(self, token: str) -> Principal:
        claims = jwt.decode(
            token,
            self.public_key_pem,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
            options={"require": ["exp", "iat", "nbf", "jti", "sub", "org", "mid"]},
        )
        try:
            permissions = frozenset(Permission(permission) for permission in claims.get("perms", []))
        except (TypeError, ValueError) as exc:
            raise jwt.InvalidTokenError("unrecognized permission") from exc
        return Principal(
            subject=str(claims["sub"]), organization_id=str(claims["org"]),
            membership_id=str(claims["mid"]), permissions=permissions,
            roles=tuple(str(role) for role in claims.get("roles", [])), email=claims.get("email"),
        )


class AuthorizationCodeService:
    def __init__(self, store: EphemeralStore, token_service: TokenService, code_ttl_seconds: int) -> None:
        self.store = store
        self.token_service = token_service
        self.code_ttl_seconds = code_ttl_seconds

    async def issue_code(self, identity: ResolvedIdentity, pkce_challenge: str, return_uri: str) -> str:
        code = secrets.token_urlsafe(48)
        record = AuthorizationCode(
            code_id=secrets.token_urlsafe(18), subject=identity.subject,
            organization_id=identity.organization_id, membership_id=identity.membership_id,
            roles=identity.roles, permissions=identity.permissions,
            pkce_challenge=pkce_challenge, redirect_uri=return_uri,
            issued_at=datetime.now(timezone.utc).isoformat(),
        )
        await self.store.put("authorization-code", code, {
            "code_id": record.code_id, "subject": record.subject,
            "organization_id": record.organization_id, "membership_id": record.membership_id,
            "roles": list(record.roles), "permissions": list(record.permissions),
            "pkce_challenge": record.pkce_challenge, "redirect_uri": record.redirect_uri,
            "issued_at": record.issued_at,
        }, self.code_ttl_seconds)
        return code

    async def exchange_code(self, code: str, code_verifier: str, redirect_uri: str) -> dict[str, Any]:
        validate_pkce_verifier(code_verifier)
        record = await self.store.consume("authorization-code", code)
        if record is None:
            raise ValueError("invalid or expired authorization code")
        expected_challenge = record["pkce_challenge"]
        if not hmac.compare_digest(_b64url_sha256(code_verifier), expected_challenge):
            raise ValueError("PKCE verification failed")
        if not hmac.compare_digest(redirect_uri, record["redirect_uri"]):
            raise ValueError("redirect URI mismatch")
        identity = ResolvedIdentity(
            subject=record["subject"], organization_id=record["organization_id"],
            membership_id=record["membership_id"], roles=tuple(record["roles"]),
            permissions=tuple(record["permissions"]), email=None,
        )
        return {
            "access_token": self.token_service.issue_access_token(identity),
            "token_type": "Bearer",
            "expires_in": self.token_service.access_ttl_seconds,
        }
