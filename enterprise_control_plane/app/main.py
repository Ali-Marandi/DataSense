"""FastAPI composition root. Deploy with an injected PostgreSQL-backed repository and Redis store."""
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Awaitable, Callable
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .auth import AuthorizationCodeService, TokenService
from .metrics import HTTP_DURATION_SECONDS, HTTP_REQUESTS
from .models import Permission, Principal, ResourceRef
from .quality_gate import QualityGateObservation, QualityGateService
from .rbac import AuditSink, PermissionMiddleware, PermissionService, require_permission
from .saml import SamlSecurityError, SamlServiceProvider


@dataclass(frozen=True)
class ControlPlaneComponents:
    saml: SamlServiceProvider
    authorization_codes: AuthorizationCodeService
    token_service: TokenService
    permission_service: PermissionService
    audit_sink: AuditSink
    quality_gate_service: QualityGateService | None = None
    ready_check: Callable[[], Awaitable[bool]] | None = None


def create_app(components: ControlPlaneComponents) -> FastAPI:
    app = FastAPI(title="DataSense Enterprise Control Plane", docs_url=None, redoc_url=None)
    app.add_middleware(PermissionMiddleware, token_verifier=components.token_service, audit_sink=components.audit_sink)

    @app.middleware("http")
    async def record_metrics(request: Request, call_next):
        started = perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            # Route templates avoid high-cardinality labels such as dataset UUIDs.
            route = request.scope.get("route")
            route_label = getattr(route, "path", "unmatched")
            status_code = str(response.status_code) if response is not None else "500"
            HTTP_REQUESTS.labels(request.method, route_label, status_code).inc()
            HTTP_DURATION_SECONDS.labels(request.method, route_label).observe(perf_counter() - started)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/health/live", include_in_schema=False)
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", include_in_schema=False)
    async def ready() -> dict[str, str]:
        if components.ready_check is None or await components.ready_check():
            return {"status": "ready"}
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="dependencies unavailable")

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

    async def organization_resource(_request: Request, principal: Principal) -> ResourceRef:
        return ResourceRef("organization", principal.organization_id, principal.organization_id)

    @app.post("/v1/governance/quality-observations", status_code=status.HTTP_202_ACCEPTED)
    async def record_quality_gate_observation(
        observation: QualityGateObservation,
        principal: Principal = Depends(require_permission(
            Permission.CONTRACT_RUN, organization_resource, components.permission_service
        )),
    ) -> dict[str, bool]:
        if components.quality_gate_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="quality observation service unavailable")
        return {"recorded": await components.quality_gate_service.record(principal, observation)}

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
