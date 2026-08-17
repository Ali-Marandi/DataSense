# Scenario <C##> — <Title>

| Field | Record |
|---|---|
| Report ID | `ACT-CHAOS-YYYYMMDD-###` |
| Environment | `test` / `staging` only |
| UTC start/end | `<timestamps>` |
| Commit/image/policy/migration | `<versions>` |
| Synthetic fixture | `<identifier; no customer data>` |
| Reviewer | `<role and name>` |

## Fault injection

Describe the exact command, fixture, or controlled failure. Confirm the environment allow-list and explicit non-production acknowledgement.

## Expected invariants

| Invariant | Expected result |
|---|---|
| Final circuit/policy state | `<expected>` |
| External fake-provider effect count | `<expected count>` |
| Outbox/activation final state | `<expected>` |
| Audit and bounded metric | `<expected>` |

## Observed evidence

Record redacted command output, UTC timeline, metrics snapshot, audit IDs, and fake-provider call count. Do not include raw payloads, identifiers, URLs, secrets, or exception text.

## Result

`PASS — model` / `PARTIAL` / `NOT RUN` / `PASS — staging` / `FAIL`

## Deviation, containment, and CAPA

State deviation, whether circuit/kill switch/rollback was used, owner, due date, and verification test. A failed critical invariant blocks rollout.

## Sign-off

| Role | Decision | Date |
|---|---|---|
| Engineering | Approve / Reject | |
| SRE | Approve / Reject | |
| Security | Approve / Reject | |
| Privacy (if applicable) | Approve / Reject / N/A | |
