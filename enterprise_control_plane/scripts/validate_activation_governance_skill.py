#!/usr/bin/env python3
"""Validate the vendored activation-governance skill and its non-production guard.

This checker is dependency-free so it can run in GitHub Actions. It validates static
skill integrity and executes only the *print-only* Wave C planner. It never contacts a
cluster, starts a worker, sends a provider request, or generates activation traffic.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "activation-governance-chaos-rollout"
PLANNER = ROOT / "enterprise_control_plane" / "scripts" / "plan_activation_wave_c_staging_dry_run.sh"

REQUIRED_FILES = (
    "SKILL.md",
    "references/chaos-scenario-matrix.md",
    "references/limited-rollout-thresholds.md",
    "templates/scenario_evidence_card.md",
    "templates/security_wave_a_signoff.md",
)


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def check_skill_files() -> None:
    for relative in REQUIRED_FILES:
        path = SKILL / relative
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            fail(f"required skill resource missing or empty: {relative}")

    skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    if not skill_text.startswith("---\n"):
        fail("SKILL.md frontmatter is missing")
    frontmatter, _, _ = skill_text[4:].partition("\n---\n")
    if "name: activation-governance-chaos-rollout" not in frontmatter:
        fail("SKILL.md name does not match the vendored skill")
    if "description:" not in frontmatter:
        fail("SKILL.md description is missing")

    required_rules = (
        "fail-closed",
        "Never redrive stale external notifications automatically",
        "--confirm-nonprod",
        "PASS — staging",
    )
    for rule in required_rules:
        if rule not in skill_text:
            fail(f"required safety instruction missing from SKILL.md: {rule}")


def run_planner_guard_checks() -> None:
    if not PLANNER.is_file():
        fail("Wave C dry-run planner is missing")

    base = [
        "bash",
        str(PLANNER),
        "--environment",
        "staging",
        "--namespace",
        "datasense-staging",
        "--scenario",
        "C08",
        "--change-id",
        "CI-DRYRUN-001",
        "--synthetic-tenant",
        "synthetic-ci-fixture",
    ]
    missing_ack = subprocess.run(base, text=True, capture_output=True, check=False)
    if missing_ack.returncode == 0:
        fail("Wave C planner accepted execution without explicit non-production acknowledgement")
    if "--confirm-nonprod" not in missing_ack.stderr:
        fail("Wave C planner rejected missing acknowledgement with an unexpected error")

    accepted = subprocess.run(base + ["--confirm-nonprod"], text=True, capture_output=True, check=False)
    if accepted.returncode != 0:
        fail(f"Wave C planner rejected a valid non-production dry-run: {accepted.stderr.strip()}")
    if "PRINT ONLY" not in accepted.stdout or "DO NOT RUN FROM THIS SCRIPT" not in accepted.stdout:
        fail("Wave C planner output no longer proves it is non-destructive")


def main() -> None:
    check_skill_files()
    run_planner_guard_checks()
    print("PASS: activation-governance skill integrity and non-production planner guards verified")


if __name__ == "__main__":
    main()
