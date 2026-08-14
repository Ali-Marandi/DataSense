"""Production composition root; all secrets are read from mounted files at process start."""
from __future__ import annotations

from .auth import AuthorizationCodeService, TokenService
from .ephemeral_store import RedisEphemeralStore
from .main import ControlPlaneComponents, create_app
from .rbac import PermissionService
from .repositories import PostgresEnterpriseRepository
from .saml import SamlServiceProvider
from .settings import get_settings


settings = get_settings()
repository = PostgresEnterpriseRepository(settings.database_url)
store = RedisEphemeralStore(settings.redis_url or "")
tokens = TokenService(
    settings.jwt_issuer,
    settings.jwt_audience,
    settings.required_secret("JWT private key", settings.jwt_private_key_pem_file),
    settings.required_secret("JWT public key", settings.jwt_public_key_pem_file),
    settings.access_token_ttl_seconds,
)
saml = SamlServiceProvider(
    store=store,
    connections=repository,
    identities=repository,
    transaction_ttl_seconds=settings.saml_transaction_ttl_seconds,
    clock_skew_seconds=settings.saml_clock_skew_seconds,
    sp_x509_cert_pem=settings.required_secret("SAML SP certificate", settings.saml_sp_x509_cert_pem_file),
    sp_private_key_pem=settings.required_secret("SAML SP private key", settings.saml_sp_private_key_pem_file),
    require_encrypted_assertion=settings.saml_encrypted_assertion_required,
)
permission_service = PermissionService(repository)
app = create_app(ControlPlaneComponents(
    saml=saml,
    authorization_codes=AuthorizationCodeService(store, tokens, settings.auth_code_ttl_seconds),
    token_service=tokens,
    permission_service=permission_service,
    audit_sink=repository,
    ready_check=repository.ready,
))


@app.on_event("startup")
async def startup() -> None:
    await repository.open()


@app.on_event("shutdown")
async def shutdown() -> None:
    await repository.close()
    await store.close()
