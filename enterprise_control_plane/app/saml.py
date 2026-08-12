"""SAML 2.0 SP-initiated flow using python3-saml; never parse assertion XML yourself."""
from __future__ import annotations

import secrets
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Protocol
from urllib.parse import urlparse

from .ephemeral_store import EphemeralStore
from .models import SamlConnection


class SamlSecurityError(Exception):
    """A deliberately non-specific authentication failure."""


@dataclass(frozen=True)
class ResolvedIdentity:
    subject: str
    organization_id: str
    membership_id: str
    roles: tuple[str, ...]
    permissions: tuple[str, ...]
    email: str | None


class ConnectionRepository(Protocol):
    async def get_enabled_by_slug(self, slug: str) -> SamlConnection | None: ...


class IdentityResolver(Protocol):
    async def resolve(self, connection: SamlConnection, external_subject: str, attributes: dict[str, list[str]]) -> ResolvedIdentity | None: ...


class SamlServiceProvider:
    def __init__(
        self,
        store: EphemeralStore,
        connections: ConnectionRepository,
        identities: IdentityResolver,
        transaction_ttl_seconds: int,
        clock_skew_seconds: int,
        sp_x509_cert_pem: str,
        sp_private_key_pem: str,
        require_encrypted_assertion: bool = True,
    ) -> None:
        self.store = store
        self.connections = connections
        self.identities = identities
        self.transaction_ttl_seconds = transaction_ttl_seconds
        self.clock_skew_seconds = clock_skew_seconds
        self.sp_x509_cert_pem = sp_x509_cert_pem
        self.sp_private_key_pem = sp_private_key_pem
        self.require_encrypted_assertion = require_encrypted_assertion

    @staticmethod
    def _validate_pkce_challenge(value: str) -> None:
        # S256 base64url length is normally 43 characters; accept RFC 7636 range only.
        if not (43 <= len(value) <= 128) or any(char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for char in value):
            raise SamlSecurityError("invalid PKCE challenge")

    @staticmethod
    def _validate_return_uri(value: str) -> None:
        parsed = urlparse(value)
        if parsed.scheme != "datasense" or parsed.netloc != "auth" or parsed.path != "/callback":
            raise SamlSecurityError("unregistered desktop redirect URI")

    def _settings(self, connection: SamlConnection) -> dict:
        return {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": connection.sp_entity_id,
                "assertionConsumerService": {
                    "url": connection.acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "x509cert": self.sp_x509_cert_pem,
                "privateKey": self.sp_private_key_pem,
            },
            "idp": {
                "entityId": connection.idp_entity_id,
                "singleSignOnService": {
                    "url": connection.idp_sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": connection.idp_x509_cert_pem,
            },
            "security": {
                "authnRequestsSigned": True,
                "logoutRequestSigned": True,
                "logoutResponseSigned": True,
                "signMetadata": True,
                "wantAssertionsSigned": True,
                "wantMessagesSigned": True,
                "wantAssertionsEncrypted": self.require_encrypted_assertion,
                "wantNameIdEncrypted": self.require_encrypted_assertion,
                "requestedAuthnContext": False,
                "allowSingleLabelDomains": False,
                "rejectDeprecatedAlgorithm": True,
            },
        }

    async def build_authn_request(self, organization_slug: str, pkce_challenge: str, return_uri: str) -> str:
        """Create SAML Redirect URL and persist a one-time transaction referenced by RelayState."""
        self._validate_pkce_challenge(pkce_challenge)
        self._validate_return_uri(return_uri)
        connection = await self.connections.get_enabled_by_slug(organization_slug)
        if connection is None:
            raise SamlSecurityError("unknown SSO connection")

        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("python3-saml must be installed") from exc

        # No browser-supplied host headers are used when creating the request.
        auth = OneLogin_Saml2_Auth({
            "https": "on",
            "http_host": urlparse(connection.acs_url).netloc,
            "server_port": "443",
            "script_name": "/v1/auth/saml/start",
            "get_data": {}, "post_data": {},
        }, self._settings(connection))
        relay_state = secrets.token_urlsafe(32)
        redirect_url = auth.login(return_to=relay_state, force_authn=False)
        request_id = auth.get_last_request_id()
        if not request_id:
            raise RuntimeError("SAML toolkit did not produce an AuthnRequest ID")
        await self.store.put("saml-transaction", relay_state, {
            "request_id": request_id,
            "organization_id": connection.organization_id,
            "organization_slug": connection.slug,
            "pkce_challenge": pkce_challenge,
            "return_uri": return_uri,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, self.transaction_ttl_seconds)
        return redirect_url

    async def process_acs(self, organization_slug: str, form_data: dict[str, str]) -> tuple[ResolvedIdentity, dict]:
        """Validate a posted SAML Response and resolve it to an active DataSense membership."""
        relay_state = form_data.get("RelayState", "")
        if not relay_state:
            raise SamlSecurityError("SP-initiated RelayState required")
        transaction = await self.store.consume("saml-transaction", relay_state)
        if transaction is None or transaction.get("organization_slug") != organization_slug:
            raise SamlSecurityError("invalid or expired SAML transaction")
        connection = await self.connections.get_enabled_by_slug(organization_slug)
        if connection is None or connection.organization_id != transaction["organization_id"]:
            raise SamlSecurityError("SSO connection no longer available")

        try:
            from onelogin.saml2.auth import OneLogin_Saml2_Auth
            from onelogin.saml2.errors import OneLogin_Saml2_Error
            request_data = {
                "https": "on",
                "http_host": urlparse(connection.acs_url).netloc,
                "server_port": "443",
                "script_name": urlparse(connection.acs_url).path,
                "get_data": {},
                "post_data": form_data,
            }
            auth = OneLogin_Saml2_Auth(request_data, self._settings(connection))
            auth.process_response(request_id=transaction["request_id"])
            if auth.get_errors() or not auth.is_authenticated():
                raise SamlSecurityError("SAML response rejected")
        except SamlSecurityError:
            raise
        except Exception as exc:
            # XML, signature, schema, issuer/audience, Destination, Recipient, NotBefore,
            # NotOnOrAfter and InResponseTo checks are enforced by strict python3-saml mode.
            raise SamlSecurityError("SAML response rejected") from exc

        assertion_id = auth.get_last_assertion_id() or auth.get_last_message_id()
        if not assertion_id:
            raise SamlSecurityError("SAML response has no replay identifier")
        # Retain IDs longer than normal assertion validity to make a captured response useless.
        accepted = await self.store.add_once("saml-replay", assertion_id, 600 + self.clock_skew_seconds)
        if not accepted:
            raise SamlSecurityError("replayed SAML response")

        attributes = auth.get_attributes()
        external_subject = auth.get_nameid()
        if not external_subject:
            raise SamlSecurityError("SAML response has no subject")
        identity = await self.identities.resolve(connection, external_subject, attributes)
        if identity is None or identity.organization_id != connection.organization_id:
            raise SamlSecurityError("no active organization membership")
        return identity, transaction
