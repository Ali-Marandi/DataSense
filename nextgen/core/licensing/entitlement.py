from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any


class EntitlementState(StrEnum):
    ACTIVE = "active"
    GRACE = "grace"
    EXPIRED = "expired"


@dataclass(frozen=True)
class FeatureDecision:
    feature: str
    allowed: bool
    state: EntitlementState
    reason: str


@dataclass(frozen=True)
class Entitlement:
    plan_name: str
    issued_at: datetime
    expires_at: datetime
    grace_until: datetime
    features: frozenset[str]

    def __post_init__(self) -> None:
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None or self.grace_until.tzinfo is None:
            raise ValueError("Entitlement timestamps must be timezone-aware.")
        if self.expires_at < self.issued_at:
            raise ValueError("Entitlement expiry cannot precede issuance.")
        if self.grace_until < self.expires_at:
            raise ValueError("Entitlement grace period cannot end before expiry.")
        if not self.plan_name.strip():
            raise ValueError("Entitlement plan name cannot be empty.")

    @classmethod
    def plan(
        cls,
        plan_name: str,
        expires_in_days: int,
        *,
        grace_period_days: int = 14,
        now: datetime | None = None,
    ) -> "Entitlement":
        if expires_in_days < 0 or grace_period_days < 0:
            raise ValueError("Entitlement durations cannot be negative.")
        feature_map = {
            "free": {"import", "profile", "chart"},
            "alpha": {"import", "profile", "chart", "trust_center", "verified_export", "projects"},
            "pro": {"import", "profile", "chart", "trust_center", "verified_export", "projects", "ml"},
        }
        if plan_name not in feature_map:
            raise ValueError(f"Unknown entitlement plan: {plan_name}")
        issued_at = now or datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(days=expires_in_days)
        return cls(
            plan_name=plan_name,
            issued_at=issued_at,
            expires_at=expires_at,
            grace_until=expires_at + timedelta(days=grace_period_days),
            features=frozenset(feature_map[plan_name]),
        )

    def state_at(self, now: datetime | None = None) -> EntitlementState:
        moment = now or datetime.now(timezone.utc)
        if moment <= self.expires_at:
            return EntitlementState.ACTIVE
        if moment <= self.grace_until:
            return EntitlementState.GRACE
        return EntitlementState.EXPIRED

    @property
    def active(self) -> bool:
        return self.state_at() is EntitlementState.ACTIVE

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "datasense.entitlement/v1",
            "plan_name": self.plan_name,
            "issued_at": self.issued_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "grace_until": self.grace_until.isoformat(),
            "features": sorted(self.features),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Entitlement":
        if payload.get("schema") != "datasense.entitlement/v1":
            raise ValueError("Unsupported entitlement cache schema.")
        try:
            return cls(
                plan_name=payload["plan_name"],
                issued_at=datetime.fromisoformat(payload["issued_at"]),
                expires_at=datetime.fromisoformat(payload["expires_at"]),
                grace_until=datetime.fromisoformat(payload["grace_until"]),
                features=frozenset(payload["features"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Entitlement cache is malformed.") from exc


class FeatureGate:
    """Offline feature decision boundary used by UI and delivery workflows."""

    def __init__(self, entitlement: Entitlement) -> None:
        self.entitlement = entitlement

    def decision(self, feature: str, *, now: datetime | None = None) -> FeatureDecision:
        state = self.entitlement.state_at(now)
        if feature not in self.entitlement.features:
            return FeatureDecision(feature, False, state, "feature_not_in_plan")
        if state is EntitlementState.EXPIRED:
            return FeatureDecision(feature, False, state, "entitlement_expired")
        if state is EntitlementState.GRACE:
            return FeatureDecision(feature, True, state, "offline_grace_period")
        return FeatureDecision(feature, True, state, "entitlement_active")

    def allows(self, feature: str, *, now: datetime | None = None) -> bool:
        return self.decision(feature, now=now).allowed


class EntitlementCache:
    """Atomic local cache for a remotely-issued entitlement payload.

    The cache itself is not a signature verifier. Production must validate a signed
    server payload before calling `save`; this class only protects against partial
    writes and malformed local storage.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, entitlement: Entitlement) -> Path:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, delete=False, suffix=".tmp") as handle:
            json.dump(entitlement.to_dict(), handle, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        os.replace(temporary_path, self.path)
        return self.path

    def load(self) -> Entitlement:
        try:
            return Entitlement.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("Entitlement cache could not be loaded.") from exc
