#!/usr/bin/env bash
# Print a non-destructive Wave C staging dry-run plan for C08/C15.
# This script never runs kubectl mutations, traffic generators, or provider calls.
set -Eeuo pipefail

ENVIRONMENT=""
NAMESPACE="datasense-staging"
SCENARIO="all"
CONFIRM_NONPROD=0
CHANGE_ID=""
SYNTHETIC_TENANT=""

usage() {
  cat <<'USAGE'
Usage:
  plan_activation_wave_c_staging_dry_run.sh \
    --environment staging --confirm-nonprod --change-id CHG-123 \
    --synthetic-tenant synthetic-chaos-01 [--namespace datasense-staging] \
    [--scenario C08|C15|all]

This command is a dry-run planner only. It prints proposed staging commands and
acceptance evidence; it does not execute mutations, kill pods, generate traffic,
or contact any provider.
USAGE
}

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 2; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --environment) ENVIRONMENT="${2:-}"; shift 2 ;;
    --namespace) NAMESPACE="${2:-}"; shift 2 ;;
    --scenario) SCENARIO="${2:-}"; shift 2 ;;
    --change-id) CHANGE_ID="${2:-}"; shift 2 ;;
    --synthetic-tenant) SYNTHETIC_TENANT="${2:-}"; shift 2 ;;
    --confirm-nonprod) CONFIRM_NONPROD=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Unknown argument: $1" ;;
  esac
done

[[ "$ENVIRONMENT" == "staging" ]] || fail "Only --environment staging is permitted."
[[ "$NAMESPACE" == "datasense-staging" || "$NAMESPACE" == datasense-staging-* ]] || fail "Namespace must be datasense-staging or datasense-staging-*."
[[ "$CONFIRM_NONPROD" == "1" ]] || fail "Refusing to print a run plan without --confirm-nonprod."
[[ -n "$CHANGE_ID" ]] || fail "--change-id is required."
[[ -n "$SYNTHETIC_TENANT" ]] || fail "--synthetic-tenant is required."
[[ "$SYNTHETIC_TENANT" != *"@"* && "$SYNTHETIC_TENANT" != *"/"* ]] || fail "Synthetic tenant must be an opaque fixture identifier."
[[ "$SCENARIO" == "C08" || "$SCENARIO" == "C15" || "$SCENARIO" == "all" ]] || fail "--scenario must be C08, C15, or all."

cat <<HEADER
===============================================================================
DataSense Wave C STAGING DRY-RUN PLAN
Change:       $CHANGE_ID
Environment:  $ENVIRONMENT (explicitly non-production)
Namespace:    $NAMESPACE
Fixture:      $SYNTHETIC_TENANT (must contain no customer data)
Scenario:     $SCENARIO
Mode:         PRINT ONLY — no mutation, no network delivery, no pod kill
===============================================================================
HEADER

cat <<'PREFLIGHT'
PRE-FLIGHT GATES — ALL MUST BE GREEN BEFORE AN APPROVED GAME DAY
[ ] Staging kube-context and namespace are independently verified by SRE.
[ ] Provider endpoint resolves to the approved fake provider; no production DNS/credentials are mounted.
[ ] Synthetic tenant is allow-listed; no customer identifiers or payloads are present.
[ ] Current image digest, policy version, migration version and circuit state are recorded.
[ ] Global and tenant kill switches have been drilled and named operators are present.
[ ] On-call primary, Security delegate, Engineering observer and Incident Commander are present.
[ ] Prometheus, Alertmanager test receiver, Grafana and audit sink are reachable.
[ ] Approved change window and rollback digest are recorded in the change ticket.

READ-ONLY PRE-FLIGHT COMMANDS TO RUN MANUALLY AFTER APPROVAL
  kubectl config current-context
  kubectl -n <namespace> get deploy,pod -l app.kubernetes.io/component=outbox-worker
  kubectl -n <namespace> get deploy,pod -l app.kubernetes.io/component=control-plane
  kubectl -n <namespace> get networkpolicy,serviceaccount,rolebinding
  kubectl -n <namespace> get configmap,secret -o name
  kubectl -n <namespace> rollout history deployment/datasense-outbox-worker
  kubectl -n <namespace> get events --sort-by=.metadata.creationTimestamp

ABORT IMMEDIATELY IF
  - context/namespace is not the approved staging target;
  - provider is not fake/sandbox or a customer fixture is present;
  - circuit/kill-switch/audit path is unavailable;
  - baseline worker health, metric scrape or rollback target is Red;
  - any unauthorized external delivery is observed.
PREFLIGHT

print_c08() {
  cat <<'C08'
-------------------------------------------------------------------------------
C08 — WORKER POD-KILL AFTER CLAIM (STAGING DRY-RUN)
Objective: prove lease recovery and at-most-one external effect using a fake provider.

Required implementation hooks before execution
  1. A synthetic activation fixture that is eligible only for the fake provider.
  2. A deterministic test checkpoint: after Outbox claim, before execution ledger/provider effect.
  3. Execution ledger uniqueness at the database boundary.
  4. Observable lease-recovery and fake-provider call-count metrics.

Planned execution sequence (DO NOT RUN FROM THIS SCRIPT)
  A. Record baseline: pending age, lease recoveries, worker health, fake-provider count.
  B. Enqueue exactly one synthetic activation event with a unique execution key.
  C. Wait for the approved test checkpoint `after_claim_before_effect`.
  D. Delete only the selected staging worker pod:
       kubectl -n <namespace> delete pod <worker-pod> --wait=false
  E. Wait for lease expiry/recovery and replacement worker readiness.
  F. Observe final event state and fake-provider call count.

Pass criteria
  - exactly one fake-provider effect across the complete run;
  - lease-recovery metric increases and final state is terminal/audited;
  - no raw payload, recipient, secret or provider URL appears in logs/metrics/evidence;
  - no cross-tenant row, retry loop or manual direct database correction;
  - circuit/kill state remains auditable throughout.

Capture for evidence card
  UTC start/end; commit/image/policy/migration versions; selected pod UID; checkpoint audit ID;
  before/after metric snapshots; final execution ledger row count; fake-provider count; reviewer sign-offs.
C08
}

print_c15() {
  cat <<'C15'
-------------------------------------------------------------------------------
C15 — 10× SYNTHETIC FLOOD AND CRITICAL-LAG CIRCUIT (STAGING DRY-RUN)
Objective: prove bounded queue behavior, signed critical-lag Open, and zero external effect after Open.

Required implementation hooks before execution
  1. Synthetic generator with an explicit non-production guard and no network route except fake provider.
  2. Configured baseline rate and an approved factor of 10; no hand-written customer fixture.
  3. Fake-provider latency/failure injection controlled by test configuration.
  4. Signed Alertmanager test receiver and persistent circuit audit state.
  5. Metric panels for oldest pending age, depth, worker health, lease recovery, outcomes and circuit state.

Planned execution sequence (DO NOT RUN FROM THIS SCRIPT)
  A. Record 15-minute baseline and confirm circuit CLOSED only for approved synthetic cohort.
  B. Start generator at exactly 10× measured baseline, bounded by an agreed max event count/duration.
  C. Inject fake-provider latency only; do not change policy/consent controls to create lag.
  D. Verify oldest pending age remains above 900 seconds for the configured alert window (2 minutes).
  E. Verify valid signed alert transitions circuit to OPEN and freezes activation release.
  F. Continue observation without creating new external effects; inspect suppression and queue metrics.
  G. Stop generator; do not auto-close. Start recovery assessment only after evidence is captured.

Pass criteria
  - Open is recorded with correlation ID after the valid alert;
  - all activation external attempts after Open are zero; new triggers are bounded suppressions;
  - no duplicate fake-provider effect and no unbounded retry/lease loop;
  - alert routing reaches SRE and Security within the agreed P1 response target;
  - recovery does not auto-close; Half-Open requires approved bounded canary.

Capture for evidence card
  baseline rate/factor/event limit; generator digest; alert payload signature result; timeline;
  oldest-age/depth/throughput/dead/retry/lease graphs; circuit audit; fake-provider count by UTC window;
  release freeze record; abort/containment actions; reviewer sign-offs.
C15
}

if [[ "$SCENARIO" == "C08" || "$SCENARIO" == "all" ]]; then print_c08; fi
if [[ "$SCENARIO" == "C15" || "$SCENARIO" == "all" ]]; then print_c15; fi

cat <<'CLOSE'
-------------------------------------------------------------------------------
POST-DRY-RUN ACTION
Create one scenario evidence card per scenario. Mark status as NOT RUN until the
approved staging procedure has actually occurred and all artifacts have been reviewed.
This planner has intentionally performed no mutation and cannot produce PASS evidence.
CLOSE
