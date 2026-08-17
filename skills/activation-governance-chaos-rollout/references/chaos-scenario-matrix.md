# Chaos Scenario Matrix

Use this reference to scope a fail-closed activation validation plan. Treat each row as `NOT RUN` until a scenario evidence card contains executable evidence.

| ID | Fault | Expected invariant | Minimum evidence |
|---|---|---|---|
| C01 | Pending age breaches critical threshold | Circuit opens; external effect count after breach is zero. | Signed alert, state audit, fake-provider count. |
| C02 | Lag recovers without approval | Circuit remains Open. | Persistent state before/after recovery. |
| C03 | Half-Open canary | Rate cap; Close requires health and approvals. | Rate trace, approval audit, state transition. |
| C04 | Policy store unavailable | `UNKNOWN → suppress`. | Timeout test, zero external call. |
| C05 | Consent revoked after enqueue | Delivery-time re-check suppresses. | Revocation timestamp, zero fake-provider call. |
| C06 | Recipient missing | Bounded `recipient_unverified` suppression. | Audit/reason counter, zero call. |
| C07 | Duplicate delivery | At-most-one external effect. | Unique execution assertion and call count. |
| C08 | Worker crash after claim | Lease recovery; at-most-one effect. | Pod kill evidence, lease metric, call count. |
| C09 | Provider timeout/5xx | Bounded retry; Open prevents a later retry effect. | Retry trace, Open audit, zero post-Open call. |
| C10 | Permanent 4xx | Dead state; ticketed redrive only. | Stable code, DLQ authorization test. |
| C11 | Invalid/raw-like payload | Reject before enqueue; no sensitive logging. | DB count zero, redacted log assertion. |
| C12 | Global kill switch | All activation routes suppress. | State audit and zero external call. |
| C13 | Tenant kill switch | Only target tenant suppresses. | A/B tenant isolation report. |
| C14 | Forged/replayed controller alert | Reject; state unchanged. | Signature/skew/nonce test. |
| C15 | Synthetic flood | Rate cap; critical lag opens circuit; no duplicate effect. | Load graph, queue metrics, fake-provider count. |
| C16 | Rollback revision | Circuit state persists; no schema/data loss. | Rollout undo, migration compatibility, probe evidence. |

## Evidence status rule

Use `PASS — staging` only after a synthetic, isolated staging execution captures command, UTC interval, commit/image/policy/migration version, metric snapshot, fake-provider external-effect count, and reviewer sign-off. Unit/model coverage is valuable but does not replace this evidence.
