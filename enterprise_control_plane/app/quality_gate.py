"""Central, idempotent Quality Gate observation hook.

Desktop clients send metadata-only observations after executing their local contract. The service
persists evidence first; it increments metrics only after a successful idempotent transaction.
"""
from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field, field_validator

from .metrics import QUALITY_GATE_DECISIONS
from .models import Principal


class QualityGateObservation(BaseModel):
    execution_id: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    contract_fingerprint: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    policy_tier: Literal["sandbox", "standard", "tier_1", "restricted"]
    decision: Literal["approved", "blocked", "not_configured"]
    score: float | None = Field(default=None, ge=0, le=100)
    critical_failures: int = Field(default=0, ge=0)
    high_failures: int = Field(default=0, ge=0)
    rule_errors: int = Field(default=0, ge=0)
    rows: int = Field(default=0, ge=0)

    @field_validator("score")
    @classmethod
    def score_only_when_evaluated(cls, value: float | None) -> float | None:
        return None if value is None else round(float(value), 1)


class QualityGateRepository(Protocol):
    async def record_quality_gate_observation(
        self, *, organization_id: str, actor_subject: str, observation: QualityGateObservation
    ) -> bool: ...


class QualityGateService:
    def __init__(self, repository: QualityGateRepository) -> None:
        self.repository = repository

    async def record(self, principal: Principal, observation: QualityGateObservation) -> bool:
        """Persist/audit first, then emit a metric exactly once per tenant execution ID."""
        inserted = await self.repository.record_quality_gate_observation(
            organization_id=principal.organization_id,
            actor_subject=principal.subject,
            observation=observation,
        )
        if inserted:
            QUALITY_GATE_DECISIONS.labels(
                decision=observation.decision,
                policy_tier=observation.policy_tier,
            ).inc()
        return inserted
