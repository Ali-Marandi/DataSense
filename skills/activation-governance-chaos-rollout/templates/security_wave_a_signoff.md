# Wave A Security Sign-off

## Release metadata

| Field | Value |
|---|---|
| Environment | `test` / `staging` |
| Commit/image/policy/migration version | |
| Cohort | synthetic or allow-listed only |
| Review owner | Security delegate |
| Decision | `APPROVE` / `APPROVE WITH CONDITIONS` / `REJECT` |

## Required security evidence

| Control | Required proof | Decision |
|---|---|---|
| Fail-closed policy | Missing/timeout/unknown policy produces bounded suppression and zero fake-provider call. | |
| Delivery-time re-check | Consent, recipient, circuit, channel and policy are re-read immediately before effect. | |
| Transaction/tenant boundary | State/audit/suppression/enqueue are atomic; RLS prevents cross-tenant read/write. | |
| Idempotency | Unique execution key proves at-most-one external effect through duplicate/retry/lease paths. | |
| Data minimization | Outbox, metrics, logs and evidence have no raw payload, recipient, secret, provider URL or exception text. | |
| Circuit/kill authority | Open/kill are auditable; Close requires recorded authorized approval; unknown defaults suppress. | |
| Controller input | Alert input is signed or mTLS-protected, fresh, environment-allowed and replay-protected. | |
| Dependency/access review | Secret boundary, RBAC, service account permissions and dependency posture are reviewed. | |

## Blocking conditions

Reject the Wave A gate if any external effect can occur with unknown/missing policy, tenant isolation is unproven, raw sensitive data appears in telemetry, circuit/kill authority can be bypassed, signed controller validation is absent, or required test evidence is missing.

## Conditions and final record

| Open condition | Severity | Owner | Due date | Retest scenario |
|---|---|---|---|---|
| | | | | |

Record reviewer name, UTC date, evidence links/IDs, and explicit decision. Verbal approval is not a sign-off.
