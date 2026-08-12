"""Domain models. Persist these with PostgreSQL in a production repository adapter."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class Permission(StrEnum):
    PROJECT_READ = "project.read"
    PROJECT_WRITE = "project.write"
    DATASET_IMPORT = "dataset.import"
    DATASET_EXPORT = "dataset.export"
    CONTRACT_READ = "contract.read"
    CONTRACT_EDIT = "contract.edit"
    CONTRACT_RUN = "contract.run"
    CONTRACT_OVERRIDE_BLOCK = "contract.override_block"
    AUDIT_READ = "audit.read"
    AUDIT_EXPORT = "audit.export"
    IDENTITY_MANAGE = "identity.manage"
    SSO_MANAGE = "sso.manage"
    ORGANIZATION_MANAGE = "organization.manage"


DEFAULT_ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "owner": frozenset(Permission),
    "admin": frozenset({
        Permission.PROJECT_READ, Permission.PROJECT_WRITE, Permission.DATASET_IMPORT,
        Permission.DATASET_EXPORT, Permission.CONTRACT_READ, Permission.CONTRACT_EDIT,
        Permission.CONTRACT_RUN, Permission.CONTRACT_OVERRIDE_BLOCK, Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT, Permission.IDENTITY_MANAGE,
    }),
    "data_steward": frozenset({
        Permission.PROJECT_READ, Permission.PROJECT_WRITE, Permission.DATASET_IMPORT,
        Permission.CONTRACT_READ, Permission.CONTRACT_EDIT, Permission.CONTRACT_RUN,
        Permission.CONTRACT_OVERRIDE_BLOCK, Permission.AUDIT_READ,
    }),
    "analyst": frozenset({
        Permission.PROJECT_READ, Permission.PROJECT_WRITE, Permission.DATASET_IMPORT,
        Permission.DATASET_EXPORT, Permission.CONTRACT_READ, Permission.CONTRACT_RUN,
    }),
    "viewer": frozenset({Permission.PROJECT_READ, Permission.CONTRACT_READ}),
    "auditor": frozenset({Permission.PROJECT_READ, Permission.CONTRACT_READ, Permission.AUDIT_READ, Permission.AUDIT_EXPORT}),
}


@dataclass(frozen=True)
class Principal:
    subject: str
    organization_id: str
    membership_id: str
    permissions: frozenset[Permission]
    roles: tuple[str, ...] = ()
    email: str | None = None

    def can(self, permission: Permission) -> bool:
        return permission in self.permissions


@dataclass(frozen=True)
class ResourceRef:
    resource_type: str
    resource_id: str
    organization_id: str


@dataclass(frozen=True)
class SamlConnection:
    organization_id: str
    slug: str
    idp_entity_id: str
    idp_sso_url: str
    idp_x509_cert_pem: str
    sp_entity_id: str
    acs_url: str
    attribute_mapping: dict[str, str] = field(default_factory=lambda: {"email": "email", "display_name": "displayName"})
    enabled: bool = True


@dataclass(frozen=True)
class SamlTransaction:
    request_id: str
    organization_id: str
    state: str
    pkce_challenge: str
    return_uri: str
    created_at: str


@dataclass(frozen=True)
class AuthorizationCode:
    code_id: str
    subject: str
    organization_id: str
    membership_id: str
    roles: tuple[str, ...]
    permissions: tuple[str, ...]
    pkce_challenge: str
    redirect_uri: str
    issued_at: str


@dataclass(frozen=True)
class AuditEvent:
    organization_id: str
    actor_subject: str | None
    action: str
    outcome: str
    resource_type: str | None = None
    resource_id: str | None = None
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat())
    details: dict[str, Any] = field(default_factory=dict)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
