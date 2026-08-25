from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.licensing.entitlement import Entitlement, EntitlementCache, EntitlementState, FeatureGate


def test_feature_gate_handles_active_grace_and_expired_states(tmp_path):
    issued = datetime(2026, 8, 26, tzinfo=timezone.utc)
    entitlement = Entitlement.plan("alpha", 1, grace_period_days=2, now=issued)
    gate = FeatureGate(entitlement)

    active = gate.decision("verified_export", now=issued + timedelta(hours=12))
    grace = gate.decision("verified_export", now=issued + timedelta(days=2))
    expired = gate.decision("verified_export", now=issued + timedelta(days=4))

    assert (active.allowed, active.state, active.reason) == (True, EntitlementState.ACTIVE, "entitlement_active")
    assert (grace.allowed, grace.state, grace.reason) == (True, EntitlementState.GRACE, "offline_grace_period")
    assert (expired.allowed, expired.state, expired.reason) == (False, EntitlementState.EXPIRED, "entitlement_expired")


def test_feature_gate_rejects_feature_outside_plan_even_during_grace():
    issued = datetime(2026, 8, 26, tzinfo=timezone.utc)
    gate = FeatureGate(Entitlement.plan("free", 0, grace_period_days=5, now=issued))

    decision = gate.decision("verified_export", now=issued + timedelta(days=2))

    assert not decision.allowed
    assert decision.reason == "feature_not_in_plan"
    assert decision.state is EntitlementState.GRACE


def test_entitlement_cache_round_trip_is_atomic_and_schema_aware(tmp_path):
    issued = datetime(2026, 8, 26, tzinfo=timezone.utc)
    entitlement = Entitlement.plan("pro", 30, now=issued)
    cache = EntitlementCache(tmp_path / "license" / "entitlement.json")

    saved_path = cache.save(entitlement)
    loaded = cache.load()

    assert saved_path.exists()
    assert loaded.to_dict() == entitlement.to_dict()


def test_entitlement_rejects_unknown_plan_invalid_durations_and_corrupt_cache(tmp_path):
    with pytest.raises(ValueError, match="Unknown entitlement"):
        Entitlement.plan("enterprise", 30)
    with pytest.raises(ValueError, match="durations"):
        Entitlement.plan("alpha", -1)

    cache = EntitlementCache(tmp_path / "entitlement.json")
    cache.path.write_text("{invalid", encoding="utf-8")
    with pytest.raises(ValueError, match="could not be loaded"):
        cache.load()
