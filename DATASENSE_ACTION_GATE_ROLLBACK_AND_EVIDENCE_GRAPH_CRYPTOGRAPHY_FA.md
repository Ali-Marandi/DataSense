# Rollback خودکار Action Gate و اعتبارسنجی رمزنگاری Evidence Graph

**نسخه:** ۱.۰ — ۲۳ اوت ۲۰۲۶
**وضعیت:** specification برای protected staging و limited production؛ هیچ بخش این سند مجوز effect خارجی بدون approval و evidence نیست.

## ۱. تعریف درست «rollback خودکار»

در سیستم‌های داده‌محور و providerهای خارجی، rollback دو مفهوم متفاوت دارد که نباید با هم اشتباه شوند. نخست، **مهار فوری اثرهای جدید** است: Gate policy، circuit یا rollout mode طوری تغییر می‌کند که action جدید اجازهٔ اثر خارجی نگیرد. دوم، **جبران اثر قبلاً رخ‌داده** است: لغو، reverse یا compensate یک effect در provider. اولی در DataSense می‌تواند خودکار، fail-closed و فوری باشد؛ دومی فقط وقتی مجاز است که provider قرارداد جبرانی idempotent و صریح داشته باشد و policy آن را مجاز بداند. حذف artifact یا ارسال reverse request بدون چنین قرارداد و approval، rollback امن نیست.

> **اصل حاکم:** rollback خودکار، actionهای آینده را متوقف می‌کند؛ evidence، receipt، audit trail و execution ledger را حذف یا بازنویسی نمی‌کند. اثر قبلی تنها با compensation قابل‌اثبات و policy-bound قابل جبران است.

## ۲. سطح‌های rollback و پیامد آن‌ها

| سطح | چه چیزی تغییر می‌کند | واکنش خودکار مجاز | چیزی که هرگز خودکار انجام نمی‌شود |
|---|---|---|---|
| R0 — Observation | فقط telemetry و shadow decision | no-op یا افزایش signal | تغییر verdict یا provider traffic |
| R1 — Gate containment | Action Gate برای scope مشخص به `suppress_external` می‌رود | block/suppress actionهای جدید، ثبت reason code | حذف receipt یا approval |
| R2 — Circuit containment | circuit tenant/scope به `OPEN` می‌رود | توقف provider attemptهای جدید؛ recovery با `HALF_OPEN` محدود | close خودکار circuit |
| R3 — Policy rollback | policy candidate از active scope برداشته و last-known-good policy انتخاب می‌شود | فقط با CAS + digest + rollback plan | relaxation یا `block → allow` خودکار |
| R4 — Artifact quarantine | artifact staged یا local-not-yet-published قرنطینه می‌شود | جلوگیری از final rename/publish | delete خارجی یا revoke نامطمئن |
| R5 — Compensating action | provider effect دارای compensation contract است | فقط workflow approved، idempotent و auditable | cancellation/reversal حدسی یا بدون provider receipt |

`R1` و `R2` باید در rollout اولیه قابل‌خودکارسازی باشند. `R3` خودکار تنها وقتی معتبر است که policy قبلی immutable، approved، سازگار با schema engine و از پیش در rollback plan ثبت شده باشد. `R5` در pilot به‌صورت پیش‌فرض ممنوع است.

## ۳. State machine کنترل rollout و rollback

Circuit breaker فعلی برای activation دارای حالت‌های `CLOSED`، `OPEN`، `HALF_OPEN`، `MANUAL_KILL` و `UNKNOWN` است. Action Gate به یک state machine جدا نیاز دارد؛ circuit و rollout state نباید جای هم استفاده شوند.

```text
SHADOW ──approval──> LIMITED_ENFORCE ──promotion──> ENFORCE
   │                       │                   │
   │                       └──── trigger ──────┤
   └──────────── trigger ──────────────────────┘
                                    ▼
                            ROLLBACK_PENDING
                                    │  CAS + audit
                                    ▼
                           ROLLBACK_ACTIVE
                           │              │
                           │              └──> MANUAL_KILL (critical / human decision)
                           ▼
                        RECOVERY_REVIEW ──approved health proof──> HALF_OPEN_LIMITED
                                                                    │
                                                                    └──> LIMITED_ENFORCE
```

`SHADOW` فقط برای مشاهده و comparison است؛ Action Gate shadow به تنهایی نباید جای کنترل‌های موجود consent، kill switch، circuit و execution ledger را بگیرد. `ENFORCE` بدون dependencyهای لازم باید fail-closed شود. `ROLLBACK_ACTIVE` دو تصمیم متمایز ثبت می‌کند: `decision_mode=shadow` برای یادگیری و `execution_mode=suppress_external` برای safety. تغییر اول بدون دومی برای action خارجی کافی نیست.

### ۳.۱ مدل حالت پایدار

```sql
CREATE TABLE action_gate_rollout_states (
  tenant_id UUID NOT NULL,
  scope TEXT NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('shadow','limited_enforce','enforce','rollback_active','manual_kill')),
  execution_mode TEXT NOT NULL CHECK (execution_mode IN ('observe_only','allow_guarded','suppress_external')),
  active_policy_digest TEXT NOT NULL,
  last_known_good_policy_digest TEXT NOT NULL,
  version BIGINT NOT NULL,
  rollback_plan_digest TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (tenant_id, scope)
);

CREATE TABLE action_gate_rollback_events (
  rollback_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,
  scope TEXT NOT NULL,
  trigger_type TEXT NOT NULL,
  trigger_evidence_digest TEXT NOT NULL,
  previous_state JSONB NOT NULL,
  target_state JSONB NOT NULL,
  transition_status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  UNIQUE (tenant_id, scope, trigger_evidence_digest)
);

ALTER TABLE action_gate_rollout_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_gate_rollback_events ENABLE ROW LEVEL SECURITY;
```

همهٔ tableها باید همان tenant RLS model Control Plane را دریافت کنند. `previous_state` و `target_state` فقط metadata، policy digest، mode و version دارند؛ payload action، recipient یا raw data نباید در rollback event ذخیره شود.

## ۴. triggerهای rollback خودکار

Trigger باید high-confidence، bounded و resistant به flapping باشد. یک status code تک یا alert غیرامضاشده نباید production mode را تغییر دهد. هر trigger به یک `trigger_evidence_digest` متناظر با metric snapshot، signed alert یا reconciliation report نیاز دارد.

| trigger class | نمونه signal | شرط پیشنهادی | واکنش خودکار اولیه |
|---|---|---|---|
| Integrity | افزایش `receipt_verification_failure` یا `evidence_binding_mismatch` | threshold versioned در دو window پیوسته | R1 + R2، quarantine producer مسیر مشکل‌دار |
| Policy safety | `policy_input_unknown` یا AST evaluation error در enforcement | هر unknown در scope external یا threshold در scope داخلی | R1؛ candidate policy freeze؛ ticket security |
| Delivery safety | duplicate effect candidate، ledger conflict، effect state غیرقابل‌تطبیق | یک event با severity critical | R2؛ worker delivery stop برای scope |
| Reliability | p95 gate latency یا dependency outage خارج از SLO | burn-rate در windows کوتاه و بلند | R1؛ degrade به suppress_external نه bypass |
| Blast-radius surprise | actual transitions از approved simulator envelope بیشتر شود | threshold policy-specific | R1 + policy rollback R3 فقط به last-known-good |
| Graph integrity | checkpoint mismatch، edge invariant violation یا batch verification failure | هر mismatch cryptographic | R1؛ graph producer quarantine؛ action allow جدید fail-closed اگر graph required است |
| Signed operational alert | allow-listed alert با HMAC، timestamp و nonce معتبر | controller acceptance | R2؛ circuit open |

Thresholdها باید در immutable `rollback_plan` policy ثبت شوند و در pilot با synthetic traffic کالیبره شوند. اعداد جهانی یا hard-code مناسب نیستند؛ trade-off latency/false-positive برای هر action taxonomy متفاوت است.

### ۴.۱ pipeline trigger تا rollback

```text
Metric / signed alert / reconciliation mismatch
             │
             ▼
   Rollback Trigger Evaluator
   - threshold window
   - source authentication
   - tenant/scope binding
   - deduplication key
             │
             ▼
   Durable Rollback Coordinator (CAS transaction)
     1. write rollback event intent
     2. set execution_mode=suppress_external
     3. open tenant/scope circuit where applicable
     4. replace candidate with approved last-known-good policy
     5. emit audit + evidence graph nodes
             │
             ▼
  Action Gate / Worker re-read state before every external attempt
```

Coordinator باید idempotent باشد. `rollback_id` یا `trigger_evidence_digest` برای یک tenant/scope فقط یک transition فعال می‌سازد. اگر compare-and-set شکست خورد، Coordinator state را دوباره می‌خواند؛ state ناشناخته یا unavailable به‌معنای `suppress_external` است، نه retry کور.

### ۴.۲ شبه‌کد Coordinator

```python
async def automatic_rollback(trigger: RollbackTrigger) -> RollbackResult:
    verify_trigger_source(trigger)                 # HMAC/mTLS/metric source + tenant binding
    plan = await repository.load_rollback_plan(trigger.tenant_id, trigger.scope)
    if not plan or not plan.allows(trigger.type):
        return RollbackResult("suppressed_plan_unavailable")

    state = await repository.get_rollout_state(trigger.tenant_id, trigger.scope)
    if state is None:
        return RollbackResult("suppressed_rollout_state_unknown")

    target = RolloutState(
        mode="rollback_active",
        execution_mode="suppress_external",
        active_policy_digest=state.last_known_good_policy_digest,
        last_known_good_policy_digest=state.last_known_good_policy_digest,
    )
    committed = await repository.cas_rollback(
        expected_version=state.version,
        trigger_evidence_digest=trigger.evidence_digest,
        target=target,
    )
    if not committed:
        return RollbackResult("rollback_already_handled_or_raced")

    # Open only; closing requires human approval and health proof.
    await circuit.open(organization_id=trigger.tenant_id, scope=trigger.scope,
                       reason_code=trigger.reason_code)
    await audit.append("action_gate_rollback_activated", metadata=target.redacted_metadata())
    return RollbackResult("rollback_active")
```

`cas_rollback` باید event intent، state update و outbox audit message را در یک تراکنش PostgreSQL ثبت کند. Circuit open اگر موقتاً unavailable باشد، state `suppress_external` همچنان در Action Gate اثر دارد؛ هیچ response `allow` به دلیل شکست circuit service صادر نمی‌شود.

## ۵. مرزهای Action Gate در rollback

### ۵.۱ Desktop: stage → gate → commit

در export desktop، Artifact ابتدا در temporary staging path ایجاد می‌شود. تنها `artifact_sha256`، action intent و evidence/receipt metadata به Gate می‌رسد. اگر rollback فعال یا verdict غیر `allow` باشد، final rename/publish رخ نمی‌دهد. Artifact temporary با retention policy کوتاه قرنطینه یا حذف محلی می‌شود؛ receipt block و audit metadata باقی می‌مانند. اگر crash بعد از rename رخ دهد، recovery به execution ledger و artifact digest مراجعه می‌کند؛ فایل دوباره صادر نمی‌شود تا وضعیت معلوم شود.

### ۵.۲ API / Agent

API و MCP wrapper باید `action_nonce` و `execution_key` کوتاه‌عمر از Gate بگیرند. Gate در rollback mode nonce جدید برای external action صادر نمی‌کند. Agent نمی‌تواند با reuse receipt قدیمی bypass کند، زیرا verifier action scope، expiry و ledger reservation را کنترل می‌کند. برای high-risk toolها، nonce یک‌بارمصرف باید در Redis/transactional store consume شود؛ replay به `suppressed_action_nonce_replayed` تبدیل می‌شود.

### ۵.۳ Outbox / Provider

مسیر worker موجود از قبل policy evaluator و execution ledger را درست پیش از `WebhookDeliveryClient` دارد. در rollback:

1. leased event قبل از provider call دوباره consent، kill switch، circuit و Action Gate rollout state را بررسی می‌کند.
2. `suppress_external` event را به suppression terminal یا retry-controlled تبدیل می‌کند؛ تصمیم به event type بستگی دارد و باید policy-bound باشد.
3. execution ledger هیچ execution key جدیدی برای effect جدید grant نمی‌کند.
4. event با `effect_recorded` هرگز دوباره provider call نمی‌زند؛ recovery فقط outbox completion را انجام می‌دهد.
5. اگر provider effect `unknown` است، auto-compensation ممنوع است؛ investigation یا provider idempotency lookup نیاز دارد.

## ۶. Recovery پس از rollback

بازگشت به `LIMITED_ENFORCE` باید دستی، evidence-driven و آهسته باشد. سیستم هرگز از `ROLLBACK_ACTIVE` مستقیم به `ENFORCE` نمی‌رود.

| گام recovery | پیش‌شرط | خروجی evidence |
|---|---|---|
| علت‌یابی | trigger root cause، policy/producer/version مشخص | incident record و timeline redacted |
| اصلاح | patch + deterministic test + policy simulation | test evidence و candidate policy digest |
| Shadow replay | synthetic cohort و fake sink | `side_effects=0` و diff report |
| Approval | Security + SRE + Policy Owner | approval record با scope و expiry |
| Half-open | cap actionهای synthetic/low-risk | probe count، latency، verification success |
| Limited enforce | فقط scope مصوب | evidence card و rollback readiness |
| Close circuit | health proven + separate approval | `half_open_to_closed` approval record |

Circuit code فعلی دقیقاً این مرز را حفظ می‌کند: ورود به `HALF_OPEN` و بستن circuit نیازمند approval record است؛ probeها cap دارند و circuit unavailable به suppress تبدیل می‌شود. این الگو باید در Action Gate recovery تکرار شود.

## ۷. Evidence Graph: مدل اجرایی دقیق‌تر

Evidence Graph یک projection قابل‌query از proofهای immutable است، نه منبع اجازهٔ action. Gate همواره Receipt را مستقل verify می‌کند؛ Graph به explanation، impact و audit کمک می‌کند و در policyهای strict می‌تواند dependency required باشد. Graph node و edge از caller اعتماد نشده دریافت نمی‌شوند؛ تنها Graph Ingestor آن‌ها را از receipt/evidence verified استخراج می‌کند.

### ۷.۱ content-addressing برای node و edge

برای هر node یک envelope canonical ساخته می‌شود:

```json
{
  "schema": "datasense.evidence-graph-node/v1",
  "tenant_id": "opaque-tenant-uuid",
  "node_type": "decision_receipt",
  "source_digest": "sha256:receipt-payload-digest",
  "metadata": {
    "outcome": "allow",
    "action_type": "export.csv",
    "policy_digest": "sha256:...",
    "expires_at": "2026-09-01T00:00:00Z"
  },
  "producer_version": "control-plane-1"
}
```

`node_digest = SHA-256(canonical_json(envelope))`. metadata باید schema-validated و allow-listed باشد. `source_digest` receipt یا evidence bundle را bind می‌کند، نه اینکه آن را تکرار کند. برای edge:

```json
{
  "schema": "datasense.evidence-graph-edge/v1",
  "tenant_id": "opaque-tenant-uuid",
  "edge_type": "AUTHORIZES",
  "from_digest": "sha256:decision-receipt-node",
  "to_digest": "sha256:action-attempt-node",
  "observed_at": "2026-09-01T00:00:00Z",
  "metadata_digest": "sha256:bounded-edge-metadata",
  "producer_version": "action-gate-1"
}
```

`edge_digest = SHA-256(canonical_json(edge envelope))`. Tenant ID در DB partition/RLS لازم است؛ اگر tenant ID خودش حساس تلقی می‌شود، API response آن را expose نمی‌کند و display IDs از opaque alias استفاده می‌کنند.

### ۷.۲ graph node/edge status

| status | معنا | رفتار Gate / Graph |
|---|---|---|
| `verified` | source signature و invariant معتبر | node/edge قابل query است. |
| `quarantined` | signature، binding یا schema نامعتبر | record forensic محدود؛ edge authoritative ساخته نمی‌شود. |
| `pending_checkpoint` | transaction persist شده اما batch root هنوز امضا نشده | query محدود؛ policy strict می‌تواند allow را متوقف کند. |
| `checkpointed` | در Merkle/checkpoint signed قرار گرفته | tamper-evident audit trail کامل. |
| `revoked_key` | signature قبلاً معتبر اما key بعداً revoked شده | past proof retained؛ action جدید مجاز نیست تا policy صریحاً رفتار را تعیین کند. |
| `retracted` | assertion بعدی، node/edge را با reason قانونی/عملیاتی supersede می‌کند | delete ممنوع؛ traversal status را نشان می‌دهد. |

## ۸. زنجیرهٔ اعتبارسنجی رمزنگاری Receipt

Receipt فعلی دو لایه دارد: outer Decision Receipt و inner Signed Evidence Bundle. هر دو canonical JSON، `SHA-256` digest و HMAC-SHA256 دارند. HMAC برای desktop/local یا verifier سازمانی که secret مشترک دارد مناسب است؛ برای Trust Exchange میان سازمان‌ها، verifier نباید secret signing را دریافت کند و باید به امضای نامتقارن مانند Ed25519 یا ECDSA با public-key discovery مهاجرت شود.

### ۸.۱ verifier داخلی HMAC — ترتیب اجباری

1. **Schema gate:** `receipt_schema` و `bundle_schema` باید exact version شناخته‌شده باشند؛ نسخهٔ نامعلوم = reject.
2. **Shape/size gate:** JSON object، required fieldها، depth/size limit، enumها و string bounds validate می‌شوند؛ parser input نامعتبر به AST تبدیل نمی‌کند.
3. **Canonicalization:** JSON با sort key، separators ثابت، `allow_nan=False` و UTF-8 canonical می‌شود. canonicalizer باید versioned و test-vector-backed باشد.
4. **Digest check:** `SHA-256(canonical payload)` محاسبه و با `payload_sha256` از طریق `hmac.compare_digest` مقایسه می‌شود.
5. **Key resolution:** `key_id` از allow-listed key registry، tenant و environment resolution می‌شود؛ key absent/revoked/expired = reject.
6. **Signature check:** `HMAC-SHA256(key, canonical payload)` با signature receipt constant-time compare می‌شود.
7. **Privacy contract:** flags مربوط به raw value/path/recipient باید `False` باشند؛ flag missing یا True = reject.
8. **Nested evidence verification:** inner bundle دقیقاً با همان مراحل digest/key/signature verify می‌شود.
9. **Binding verification:** `evidence_binding.evidence_bundle_sha256` باید با digest inner bundle برابر باشد؛ lineage digest و policy digest نیز با fields extract شده تطبیق می‌یابند.
10. **Temporal/action/tenant checks:** expiry، clock skew policy، expected action type/risk/purpose، tenant from principal و policy version بررسی می‌شوند.
11. **Replay / execution control:** Receipt presence authorization نیست. Gate یک `execution_key` / `action_nonce` را در ledger reserve و consume می‌کند؛ duplicate use = suppress.
12. **Decision rule:** فقط receipt با outcome `allow` و همهٔ checks موفق به action می‌رسد. `approval_required` یا `block` proof هستند، نه capability token.

```text
untrusted JSON
  → strict parse + schema + bounds
  → canonical digest
  → key status + HMAC receipt
  → privacy constraints
  → canonical digest + HMAC evidence bundle
  → evidence/policy/lineage binding
  → expiry + action + tenant + nonce/ledger
  → ALLOW only if every gate passes
```

### ۸.۲ key lifecycle

| قابلیت | HMAC local/pilot | Enterprise / Trust Exchange target |
|---|---|---|
| Key storage | secret file خارج از source control | KMS/HSM یا managed key service |
| `key_id` | file/key registry identifier | issuer + key ID + validity interval |
| Rotation | dual-verify window محدود | overlapping public-key set و retirement policy |
| Receiver verification | فقط trusted organization verifier | public-key verification بدون secret disclosure |
| Revocation | deny-list key ID و stop issuing | signed key-status endpoint/cache with TTL |
| Audit | key ID فقط، نه material | key operation event + approval + rotation evidence |

Key material هرگز در Receipt، Evidence Graph، log، metric label یا exception message ثبت نمی‌شود. Key resolver نیز نباید fallback به کلید پیش‌فرض یا cross-tenant key داشته باشد.

### ۸.۳ upgrade به امضای نامتقارن

برای v1، HMAC یک control داخلی مناسب است ولی مالک signature و verifier secret یکسان هستند. برای exchange میان سازمان‌ها، envelope پیشنهاد می‌شود:

```json
{
  "algorithm": "Ed25519",
  "issuer": "datasense.example.invalid",
  "key_id": "issuer-key-2026-09",
  "signed_at": "2026-09-01T00:00:00Z",
  "value": "base64url-signature"
}
```

Verifier key را از registry pinned یا discovery endpoint authenticated می‌گیرد، `issuer`/tenant/environment را validate می‌کند، `signed_at` را با key validity interval می‌سنجد و signature را روی canonical payload verify می‌کند. مهاجرت باید dual-sign / dual-verify باشد؛ HMAC receipt قدیمی حذف نمی‌شود، اما action خارجی جدید پس از cutover فقط با algorithm policy-approved پذیرفته می‌شود.

## ۹. Merkle checkpoint و tamper-evidence برای Graph

HMAC receipt نشان می‌دهد issuer دارای key، payload مشخصی را امضا کرده است. Graph باید علاوه بر این، insertion sequence و batch completeness را قابل‌بررسی کند. راه پیشنهادی:

1. Graph transaction verified node/edge digestها را append-only ذخیره می‌کند.
2. در هر batch bounded، digests مرتب‌شده (canonical order) به leaves یک Merkle tree تبدیل می‌شوند.
3. `merkle_root` همراه batch ID، tenant partition، previous checkpoint digest، time window و producer version canonical شده و با organization signing key امضا می‌شود.
4. checkpoint در immutable/WORM-capable storage یا versioned object store، جدا از primary DB، anchor می‌شود.
5. API audit یک inclusion proof برای node/edge و checkpoint signature برمی‌گرداند.
6. reconciliation job دوباره leaves/root را محاسبه می‌کند؛ mismatch یک rollback trigger class `graph_integrity_mismatch` است.

```text
Receipt digest ─┐
Evidence digest ├─> verified graph leaves ─> Merkle root ─> signed checkpoint
Edge digest ────┘                                      │
                                                        └─> immutable anchor + inclusion proof
```

Checkpoint هرگز evidence/action authorization را جایگزین نمی‌کند. کاربرد آن proof of inclusion، tamper detection، audit و تشخیص حذف/reorder احتمالی است.

## ۱۰. Graph Ingestor: transaction و verification

```python
async def ingest_receipt(receipt_json, principal):
    receipt = parse_strict(receipt_json)
    verification = verify_decision_receipt(
        receipt,
        resolver=key_registry.for_tenant(principal.tenant_id),
        expected_action=None,
    )
    if not verification.valid:
        return quarantine(receipt_digest_or_input_hash(receipt_json), verification.reason)

    nodes, edges = extract_allowlisted_graph_projection(receipt)
    validate_tenant_binding(nodes, edges, principal.tenant_id)
    validate_edge_invariants(nodes, edges)
    async with repository.transaction():
        repository.upsert_content_addressed_nodes(nodes)
        repository.upsert_content_addressed_edges(edges)
        repository.append_ingestion_audit(verification.receipt_digest)
        repository.enqueue_checkpoint_batch(nodes, edges)
    return IngestResult(status="pending_checkpoint")
```

Extractor نباید node/edge پیشنهادی client را قبول کند. Edge `AUTHORIZES` تنها پس از این‌که Action Gate execution ledger completion را ثبت کرد ایجاد می‌شود. Edge `EMITS` تنها به artifact digestی که final commit شده است متصل می‌شود. این ترتیب از «گراف زیبا اما دروغین» جلوگیری می‌کند.

## ۱۱. آزمون‌های رمزنگاری، rollback و Graph

| گروه | آزمون ضروری | PASS condition |
|---|---|---|
| Canonicalization | ترتیب متفاوت keyها، Unicode، عددهای نامعتبر، NaN | digest و signature test vector مطابق؛ malformed reject. |
| Receipt tamper | تغییر action، outcome، policy/evidence digest یا expiry | verifier reject؛ Gate effect = 0. |
| Key lifecycle | unknown/revoked/wrong-tenant/expired key ID | verifier reject؛ audit bounded reason code. |
| Nested evidence | evidence bundle تغییر کرده یا binding mismatch | receipt reject حتی اگر outer shape معتبر باشد. |
| Replay | reuse receipt/action nonce/execution key | action دوم suppressed؛ provider call count unchanged. |
| Circuit rollback | signed alert replay/clock skew/wrong env | no circuit transition؛ replay counter increments. |
| Auto rollback | trigger dedupe/CAS race/dependency failure | یک R1/R2 transition، no unsafe allow، audit event present. |
| Ledger recovery | crash before/after provider effect | no uncontrolled duplicate effect؛ state reconciled. |
| Graph ingestion | forged node/edge، cross-tenant edge، invariant break | quarantine/reject؛ authoritative edge absent. |
| Checkpoint | leaf tamper/delete/reorder | Merkle/root reconciliation mismatch; rollback trigger raised. |
| Privacy | raw value/path/recipient in receipt/node/edge/log | test fails; storage write blocked. |

## ۱۲. Definition of Done

Rollback و Graph crypto تنها وقتی ready for limited production هستند که trigger-to-containment latency اندازه‌گیری شده، rollback در synthetic tenant بدون provider واقعی اثبات شده، close/recovery نیازمند human approval است، receipt/evidence tampering و nonce replay coverage خودکار دارند، Graph checkpoint reconciliation اجرا شده، RLS A/B tenant tests پاس شده و evidence card شامل commit/image/policy/rollback-plan digest، timestamps UTC، metric snapshots، signed approvals و fake-sink effect count باشد.

## References

[1] [Soda — AI for Data Quality, June 2026](https://soda.io/blog/ai-for-data-quality)

[2] [Acceldata — What “Good” Data Governance Looks Like in 2026](https://www.acceldata.io/blog/what-modern-data-governance-actually-looks-like-in-2026)

[3] [Drata — Introducing AI Agent Governance, June 2026](https://drata.com/blog/introducing-ai-agent-governance)
