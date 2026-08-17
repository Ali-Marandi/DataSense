# Limited Production Thresholds

Use these as initial cohort thresholds, not permanent SLOs. Calibrate only after sufficient stable evidence.

| Signal | Initial threshold | Severity | First containment |
|---|---:|---|---|
| Compliance violations | Any increase in 5m | Critical | Open global circuit and pause external channel. |
| Revocation enforcement p95 | >300s for 5m | Critical | Pause affected external scope; investigate policy/cache/worker. |
| Oldest Outbox pending age | >900s for 2m | Critical | Open circuit and freeze activation release. |
| Worker unavailable | `up == 0` for 2m | Critical | Pause external effects; recover workload through approved runbook. |
| Oldest pending age | >300s for 5m | High | Triage worker, DB, provider, and queue ownership. |
| Dead ratio | >1% for 10m | High | Pause affected route; classify error; no automatic redrive. |
| Retry ratio | >20% for 10m | High | Investigate provider and circuit behavior. |
| Payload rejection burst | >5 in 5m | High | Freeze producer/release; inspect schema with redacted logs. |
| Lease recoveries | >3 in 15m | High | Investigate worker crash/restarts/lease timing. |
| Policy denial ratio | >25% with >20 decisions in 15m | Warning | Compare policy, consent, and configuration version. |
| External blocked events | >10 in 15m | Warning | Inspect recipient/configuration; never bypass suppression. |
| Activation state age | >86400s for selected onboarding states | Warning | Product/CS human review; do not force notification. |

## Response targets

| Severity | Acknowledge | Contain | Core responders |
|---|---:|---:|---|
| Critical | 5 minutes | 10 minutes | SRE, Security; add Privacy for consent/data, Engineering for code/release. |
| High | 15 minutes | 30 minutes | SRE plus relevant Engineering/Security/Privacy owner. |
| Warning | 1 hour in release window | End of shift | Product/CS or SRE according to the signal. |

## Recovery gate

Move from Open to Half-Open only after oldest pending age is below 300 seconds for 15 minutes, workers are healthy, the dead trend is stable, compliance violations are zero since Open, and SRE plus Security approve. Close only after a bounded canary and Product approval. Do not auto-close.
