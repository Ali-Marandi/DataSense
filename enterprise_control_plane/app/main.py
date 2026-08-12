"""FastAPI composition root. Deploy with an injected PostgreSQL-backed repository and Redis store."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from .auth import AuthorizationCodeService, TokenService
from .models import Permission, ResourceRef
from .rbac import AuditSink, PermissionMiddleware, PermissionService, require_permission
from .saml import SamlSecurityError, SamlServiceProvider


@dataclass(frozen=True)
class ControlPlaneComponents:
    saml: SamlServiceProvider
    authorization_codes: AuthorizationCodeService
    token_service: TokenService
    permission_service: PermissionService
    audit_sink: AuditSink


def create_app(components: ControlPlaneComponents) -> FastAPI:
    app = FastAPI(title="DataSense Enterprise Control Plane", docs_url=None, redoc_url=None)
    app.add_middleware(PermissionMiddleware, token_verifier=components.token_service, audit_sink=components.audit_sink)

    @app.get("/health/live", include_in_schema=False)
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/auth/saml/{organization_slug}/start", include_in_schema=False)
    async def saml_start(organization_slug: str, pkce_challenge: str, return_uri: str) -> RedirectResponse:
        try:
            location = await components.saml.build_authn_request(organization_slug, pkce_challenge, return_uri)
        except SamlSecurityError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid SSO request")
        return RedirectResponse(location, status_code=status.HTTP_302_FOUND)

    @app.post("/v1/auth/saml/{organization_slug}/acs", include_in_schema=False)
    async def saml_acs(
        organization_slug: str,
        SAMLResponse: str = Form(...),
        RelayState: str = Form(...),
    ) -> RedirectResponse:
        try:
            identity, transaction = await components.saml.process_acs(organization_slug, {
                "SAMLResponse": SAMLResponse,
                "RelayState": RelayState,
            })
            code = await components.authorization_codes.issue_code(
                identity, transaction["pkce_challenge"], transaction["return_uri"]
            )
        except SamlSecurityError:
            # In production also emit a structured audit event without raw SAMLResponse.
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="SSO validation failed")
        return RedirectResponse(
            f"{transaction['return_uri']}?{urlencode({'code': code})}", status_code=status.HTTP_303_SEE_OTHER
        )

    @app.post("/v1/auth/token", include_in_schema=False)
    async def token_exchange(
        grant_type: str = Form(...),
        code: str = Form(...),
        code_verifier: str = Form(...),
        redirect_uri: str = Form(...),
    ) -> dict:
        if grant_type != "authorization_code":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported grant type")
        try:
            return await components.authorization_codes.exchange_code(code, code_verifier, redirect_uri)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid grant")

    async def dataset_resource(request: Request, _principal) -> ResourceRef:
        # Real implementation must load a row filtered by principal.organization_id,
        # then map it to ResourceRef. Never accept organization_id from the client.
        dataset_id = request.path_params["dataset_id"]
        organization_id = request.headers.get("X-DataSense-Test-Organization", "")
        if not organization_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
        return ResourceRef("dataset", dataset_id, organization_id)

    @app.get("/v1/datasets/{dataset_id}")
    async def get_dataset(
        dataset_id: str,
        _principal=Depends(require_permission(Permission.PROJECT_READ, dataset_resource, components.permission_service)),
    ) -> dict[str, str]:
        return {"dataset_id": dataset_id, "status": "authorized"}

    return app
