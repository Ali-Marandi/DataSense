---
name: activation-governance-chaos-rollout
description: Design, validate, and govern fail-closed customer-activation automations that use an Outbox/worker pattern. Use for activation triggers, consent and policy gates, transactional Outbox delivery, circuit breakers, kill switches, chaos validation, limited-production rollout gates, on-call runbooks, and security sign-off packages.
---

# Activation Governance, Chaos, and Rollout

## Use this skill when

Use this skill when an automation can create an external customer effect and must be governed by policy, consent, recipient verification, transactional delivery, or production rollout gates. Apply it to systems using an Outbox, retries, DLQ, worker leases, Alertmanager, Kubernetes, or staged releases.

Do not use it to send customer messages, enable a real provider, operate production Kubernetes, or treat a design document as deployment evidence.

## Non-negotiable safety rules

1. Default to **fail-closed**. Missing policy, unknown circuit state, unavailable consent store, unverified recipient, or invalid channel must produce a bounded `suppressed` outcome with no external call.
2. Keep activation event types isolated from audit, security, Quality Gate, and other critical event classes.
3. Write activation state, audit, suppression, and Outbox enqueue atomically and tenant-scoped. Use a unique execution key to obtain at-most-one external effect.
4. Re-evaluate policy, consent, recipient, circuit, and channel immediately before external delivery. Do not rely only on enqueue-time approval.
5. Never redrive stale external notifications automatically. Generate a new trigger only after a fresh eligibility evaluation.
6. Run chaos only with synthetic data, a fake provider, an explicit non-production acknowledgement, and an allow-listed environment. Do not run destructive or load commands against production.
7. Never put customer identifiers, payloads, provider URLs, secrets, or raw exception text in metric labels, evidence cards, or incident channels.

## Workflow

### 1. Establish the evidence baseline

Read the implementation, schema, worker, metrics, deployment manifests, existing tests, and release runbooks. Create a scenario register using `templates/scenario_evidence_card.md`.

Classify each scenario precisely:

| Status | Meaning |
|---|---|
| `PASS — model` | Deterministic in-memory/unit evidence only. |
| `PARTIAL` | Some implementation or test exists; acceptance criterion is incomplete. |
| `NOT RUN` | Design intent exists but no executable evidence. |
| `PASS — staging` | Isolated, non-production, integration/staging execution has complete evidence. |
| `FAIL` | An invariant or acceptance criterion did not hold. |

Do not generalize a model PASS to staging or production readiness.

### 2. Define the circuit and policy boundary

Specify event classes, allowed channels, circuit states, state-transition authority, and expected suppression reason codes. Use the default state model below unless the project has a stricter one:

| State | External delivery | Transition rule |
|---|---|---|
| `CLOSED` | Allowed only after all gates pass. | Critical lag/policy breach/kill condition opens circuit. |
| `OPEN` | Forbidden; suppress. | May move to Half-Open only with evidence and approval. |
| `HALF_OPEN` | Fixed low-rate canary only. | Any unexpected failure returns to Open. |
| `MANUAL_KILL` | Forbidden; suppress. | Authorized human recovery only after incident review. |
| `UNKNOWN` | Forbidden; suppress. | Restore trusted state and obtain approval. |

Require a signed or mTLS-protected alert/controller input. Prometheus or an untrusted webhook must not directly gain permission to close a circuit or patch a deployment.

### 3. Build a scenario remediation plan

For each PARTIAL or NOT RUN scenario, define the missing control, a synthetic fault injection, assertions for external-effect count/final state/audit/metrics, the required environment and reviewer, and the precise artifact required for PASS.

Read `references/chaos-scenario-matrix.md` for baseline scenario families and `references/limited-rollout-thresholds.md` for operational gates. Prioritize consent, tenant isolation, policy availability, signed controller input, execution idempotency, and kill-switch behavior before capacity or growth tests.

### 4. Run tests in tiers

Run in this order:

1. **Unit/model:** state transitions, signature parsing, reason classification, rate cap.
2. **Integration:** isolated database/Redis/fake provider; test revocation after enqueue, idempotency, retry/dead, schema rejection, and tenant isolation.
3. **Staging game day:** synthetic tenant only; validate Alertmanager/controller, worker crash, flood, rollback, metrics, alert routes, and audit persistence.

Every staging command must require an environment allow-list and an explicit `--confirm-nonprod`-style acknowledgement. A missing acknowledgement must exit non-zero.

### 5. Operate Limited Production

Before enabling a cohort, verify kill switch, circuit audit, worker health, dashboard scrape, rollback target, pager routing, current policy version, and named on-call owners. Treat a compliance violation, slow revocation, critical Outbox lag, or worker unavailability as a safety event; pause external delivery before optimizing recovery.

Use the threshold reference only as an initial cohort baseline. Calibrate it after sufficient stable evidence; do not declare a contractual SLO from an initial pilot.

### 6. Close evidence and decide

Require a scenario evidence card, UTC timing, commit/image/policy/migration version, redacted metrics, fake-provider external-effect count, and reviewer sign-off. A critical failure, unknown circuit behavior, missing tenant isolation evidence, or unexecuted critical scenario blocks broad rollout.

| Decision | Minimum condition |
|---|---|
| Keep internal/staging | Critical scenario has no staging evidence. |
| Limited Production | P0 scenarios are staging PASS; alert routing and Security/SRE/Privacy/Engineering/Product sign-offs exist. |
| Expand cohort | Stable operating evidence, zero open critical findings, capacity review, and recorded governance approval. |
| Broad Production | All required scenarios staging PASS, rollback drill PASS, calibrated alerts, complete CAPA closure, and formal sign-offs. |

## Required artifacts

Create or update only the artifacts needed by the project: scenario register/evidence cards, remediation/CAPA plan, security sign-off package, Limited Production on-call runbook, post-incident/validation report, and executive decision briefing.

Keep design status, executable test status, and production status visibly separate in all artifacts.

## Resources

- Read `references/chaos-scenario-matrix.md` when designing or validating a chaos plan.
- Read `references/limited-rollout-thresholds.md` when defining alerts, escalation, or release gates.
- Copy `templates/scenario_evidence_card.md` for each test scenario.
- Copy `templates/security_wave_a_signoff.md` for security review before activation integration is enabled.

## Completion checklist

- [ ] All external effects are policy-gated and re-checked at delivery time.
- [ ] Circuit and kill switch default to suppress under uncertainty.
- [ ] Test environment, synthetic fixtures, and fake provider are explicit.
- [ ] Scenario status is evidence-based and not overstated.
- [ ] Metrics use bounded, low-cardinality labels and no sensitive data.
- [ ] Open/Close/rollback authority and escalation are documented.
- [ ] Sign-offs, CAPA owners, and acceptance evidence are recorded.
