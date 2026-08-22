# نقشهٔ راه رهبری بازار و معماری Policy Simulator / Evidence Graph

**نسخه:** ۱.۰ — ۲۳ اوت ۲۰۲۶
**مالک پیشنهادی:** Product، Data Platform و Security Engineering
**وضعیت:** specification معماری؛ هیچ بخش آن مجوز اجرای production یا auto-remediation نیست.

## ۱. هدف استراتژیک

DataSense باید در ۱۲ ماه به‌جای رقابت در feature-list ابزارهای کیفیت داده، یک لایهٔ استاندارد برای **تصمیم داده‌محور قابل‌اثبات** بسازد. معیار رهبری بازار، تعداد dashboard یا model نیست؛ این است که یک سازمان بتواند برای هر export، گزارش یا action خودکار حساس، به دو پرسش در چند ثانیه پاسخ دهد: «آیا این action در زمان اجرا مجاز بود؟» و «کدام evidence، policy، lineage و approval به آن تصمیم منجر شد؟»

این جایگاه از الگوی جاری بازار متمایز است. Data-quality workflowهای agentic بر قراردادهای اجرایی و approval انسانی تکیه می‌کنند؛ governance مدرن به metadata، lineage پیوسته و enforcement در runtime نیاز دارد؛ و AI-agent governance به کنترل پیش از action، نه صرفاً alert پس از آن، حرکت می‌کند.[1] [2] [3] DataSense باید این نیازها را در یک grammar قابل‌حمل، privacy-first و action-scoped متحد کند.

> **اصل محصول:** هیچ Action Gate نباید از dashboard یا AI recommendation مشتق شود؛ تنها یک Receipt امضاشده، منقضی‌نشده، action-matched و evidence-bound می‌تواند مجوز `allow` ایجاد کند.

## ۲. نقشهٔ راه ۱۲ ماهه برای رهبری بازار

### ۲.۱ معیارهای مرحله‌ای و gateهای تصمیم

| بازه | محصول و قابلیت | evidence موفقیت | gate ادامه | شرط توقف یا narrow کردن |
|---|---|---|---|---|
| ماه ۱ | Decision Receipt Core، signature/expiry/scope verification و UI صدور receipt | test suite، demo با دادهٔ synthetic، ۳ interview problem-led | design partner بپذیرد receipt را در review ببیند | proof قابل‌حمل دغدغه نیست؛ روی Action Gate desktop متمرکز شویم. |
| ماه ۲ | Action Gate برای HTML report و CSV/XLSX export؛ reason-code UX و receipt sidecar | ۵ workflow واقعی بدون bypass؛ timing telemetry metadata-only | بیش از ۶۰٪ کاربران مفهوم allow/block را در یک جلسه بفهمند | bypass یا confusion زیاد است؛ taxonomy و UX بازطراحی شود. |
| ماه ۳ | Receiver verifier CLI/SDK و pilot با یک receiver مستقل | receipt در محیط گیرنده verify شود؛ raw data از boundary عبور نکند | حداقل یک buyer security/compliance sponsor معرفی شود | receiver proof را ارزشمند نداند؛ segment را regulated/local-first محدود کنیم. |
| ماه ۴ | Policy Simulator MVP با replay immutable و ChangeSet | policy owner قبل از deploy blast-radius report را review کند | zero side effect در همه simulation runها | policy source/version غیرقابل‌تعیین است؛ ابتدا policy registry بسازیم. |
| ماه ۵–۶ | Evidence Graph MVP، approval workflow و enterprise ledger/RBAC binding | پاسخ به inquiry «چرا block/allow شد؟» زیر ۵ دقیقه؛ ۱۰۰٪ receiptهای پایلوت قابل‌ردیابی | ۲ design partner یک workflow recurring داشته باشند | graph صرفاً visualization تلقی شود؛ روی queryهای audit-root-cause تمرکز کنیم. |
| ماه ۷ | Policy Simulator diff، impact cohort و exception-expiry | هر policy change دارای impact report و owner approval باشد | policy change بدون simulation در protected env ممکن نباشد | cost replay بالا است؛ sampling/versioned indexes اعمال شود. |
| ماه ۸–۹ | Agent Trust Gateway برای CLI/MCP/API، service identity و action nonce | agent بدون allow receipt نتواند action حساس انجام دهد | red-team test، replay test و negative control موفق باشد | agent integration ارزش واقعی ندارد؛ gateway را فقط برای workflowهای API نگه داریم. |
| ماه ۱۰ | Verifiable Trust Exchange SDK، key discovery profile و independent verifier package | دو سازمان receipt مشترک را offline verify کنند | third-party integration contract امضا شود | key/identity interoperability آماده نیست؛ exchange را beta نگه داریم. |
| ماه ۱۱ | Domain Trust Pack اول، مانند regulated analytics یا financial reporting | template با design partner و false-positive loop محدود | measurable contract/receipt reuse | domain assumptions عمومی‌اند؛ pack را متوقف یا narrow کنیم. |
| ماه ۱۲ | Enterprise GA decision: packaging، support runbook، security assessment و reference architecture | retention cohort، sponsor اقتصادی، security acceptance و incident evidence | فقط با metricهای زیر GA | در غیر این‌صورت limited production ادامه یابد. |

### ۲.۲ North Star و anti-vanity metrics

| طبقه | شاخص | تعریف قابل‌اندازه‌گیری | ضدشاخص که باید مراقبش بود |
|---|---|---|---|
| North Star | **Verified Trusted Actions** | تعداد actionهایی که receipt معتبرِ action-matched داشته و receiver یا gate آن را verify کرده است. | شمار صرف receipt صادرشده؛ receipt بلااستفاده ارزش مشتری نیست. |
| Adoption | Time to First Trusted Action | زمان import تا نخستین action همراه proof. | زمان ساخت account یا clickهای dashboard. |
| Safety | Unauthorized-action prevention rate | actionهای حساسِ نداشتن receipt معتبر که fail-closed مسدود شده‌اند، با بازبینی false positive. | تعداد block بدون بررسی impact. |
| Trust | Receipt verification success rate | سهم verification مستقل معتبر، منقضی‌نشده و action-scoped. | signature success بدون receiver واقعی. |
| Policy | Simulated blast-radius review coverage | سهم policy changes با simulation و approval پیش از deploy. | تعداد policy versionها. |
| Retention | Reuse of policy/contract/receipt patterns | reuse بعد از هفتهٔ چهارم، به تفکیک tenant و workflow. | daily active users بدون outcome. |
| Commercial | Security-backed pilot-to-paid | پایلوتی که sponsor امنیت یا compliance در تبدیل دخیل است. | leadهای بدون budget owner. |

## ۳. Policy Simulator: هدف و اصل طراحی

Policy Simulator یک **Counterfactual Lab** است، نه یک engine جدید برای اجرای واقعی. سؤال آن چنین است:

> اگر policy candidate با نسخهٔ `P_new` در زمان صدور receiptهای تاریخی یا روی action intentهای آینده برقرار بود، کدام تصمیم‌ها از `allow` به `approval_required` یا `block` تغییر می‌کردند و چرا؟

این قابلیت باید قبل از آنکه policy به Action Gate واقعی برسد، اثر آن را با evidence immutable و بدون provider call، network mutation، export یا trigger بررسی کند. بنابراین simulation همواره **side-effect-free**، **deterministic** و **reproducible** است.

### ۳.۱ مرزهای قطعی امنیتی

| قاعده | پیاده‌سازی لازم | دلیل |
|---|---|---|
| No provider call | Simulation runtime هیچ adapter outbox/provider/MCP را import یا invoke نمی‌کند. | جلوگیری از تبدیل preview به action. |
| Immutable input | فقط receipt، evidence bundle، policy snapshot و approval snapshot versioned خوانده می‌شوند. | replay باید بازتولیدپذیر باشد. |
| Tenant confinement | `tenant_id` از session و RLS می‌آید؛ cross-tenant query fail-closed است. | blast radius نباید metadata سازمان دیگر را نشان دهد. |
| Raw-data exclusion | inputها digest، bounded metadata و aggregate outcome هستند؛ row یا PII وارد simulation نمی‌شود. | local-first/privacy contract حفظ شود. |
| Candidate validation | policy candidate قبل از replay parse، schema validate و static analyze می‌شود. | policy malformed نباید نتیجهٔ ساختگی دهد. |
| Explainability | هر outcome دارای bounded `reason_codes` و input digests است. | owner باید بداند چه چیزی تغییر کرده، نه فقط count. |
| Approval separation | simulation approval را جعل نمی‌کند؛ approval hypothetical با state جدا و واضح مشخص می‌شود. | جلوگیری از برداشت غلط «approved in simulation». |

### ۳.۲ معماری مرجع

```text
Policy Registry ──── candidate policy ─────┐
                                           ▼
Receipt / Evidence / Approval Snapshot ─► Snapshot Loader ─► Input Normalizer
                                                      │                 │
                                                      │                 ▼
                                                      │       Deterministic Policy Evaluator
                                                      │                 │
                                                      ▼                 ▼
                                              Baseline Evaluator    Candidate Evaluator
                                                      │                 │
                                                      └─────── Diff & Cohort Engine ───────┐
                                                                                           ▼
                                                        Immutable Simulation Report + Signature
                                                                                           │
                                                                                 UI / API / Approval Gate
```

### ۳.۳ مدل policy و grammar پیشنهادی

v1 باید grammar محدود و deterministic داشته باشد. زبان natural-language یا LLM هرگز مستقیماً executable policy نیست؛ اگر Copilot در آینده پیشنهاد تولید کند، خروجی فقط draft است و باید به schema زیر parse، review و sign شود.

```yaml
schema: datasense.policy/v1
policy_id: external-export-restricted
version: 2026.09.0
scope:
  action_types: [export.csv, export.xlsx, report.html]
  risks: [internal, external, autonomous]
rules:
  - id: require-approved-quality
    when: quality_gate.decision != approved
    outcome: block
    reason_code: quality_gate_not_approved
  - id: block-schema-drift
    when: schema_drift.decision == blocked
    outcome: block
    reason_code: schema_drift_blocked
  - id: require-external-approval
    when: action.risk in [external, autonomous]
    outcome: approval_required
    reason_code: action_risk_requires_approval
metadata:
  owner: data-governance@example.invalid
  reviewed_at: 2026-09-01T00:00:00Z
```

Policy engine باید اولویت ثابت داشته باشد: `block` بر `approval_required` و `approval_required` بر `allow`. اگر state، field یا policy version نامعلوم باشد، نتیجه `block` با reason code مانند `policy_input_unknown` است.

### ۳.۴ ورودی و خروجی فنی

| شیء | فیلدهای کلیدی | retention | نکتهٔ فنی |
|---|---|---|---|
| `PolicySnapshot` | `policy_id`, `version`, `sha256`, canonical document، owner، approval digest | immutable | candidate و baseline هر دو hash می‌شوند. |
| `ReceiptSnapshot` | `receipt_digest`, `issued_at`, action type/risk/purpose، decision، policy version، evidence digest | metadata-only | receipt signature باید پیش از snapshot validate شود. |
| `EvidenceSnapshot` | evidence digest، gate decision، drift decision، lineage digest، sensitivity class summary | metadata-only | receipt به evidence digest bind می‌شود. |
| `ApprovalSnapshot` | approval id/digest، state، expiry، approver role | metadata-only | approval revoked/expired باید distinguish شود. |
| `SimulationRun` | run ID، tenant ID، baseline/candidate hash، time range، cohort definition، requester | immutable + auditable | هیچ outcome خام source را mutation نمی‌کند. |
| `SimulationOutcome` | receipt digest، baseline outcome، candidate outcome، delta class، reason-code diff | configurable retention | نگهداری row-level metadata با privacy review. |

نمونهٔ خروجی aggregate:

```json
{
  "simulation_id": "sim_01J...",
  "baseline_policy_sha256": "...",
  "candidate_policy_sha256": "...",
  "cohort": {"from": "2026-08-01T00:00:00Z", "to": "2026-08-31T00:00:00Z", "count": 1842},
  "blast_radius": {
    "unchanged": 1608,
    "allow_to_approval_required": 147,
    "allow_to_block": 63,
    "approval_required_to_block": 24,
    "block_to_allow": 0
  },
  "top_reason_deltas": [
    {"reason_code": "action_risk_requires_approval", "newly_affected": 147},
    {"reason_code": "schema_drift_blocked", "newly_affected": 63}
  ],
  "side_effects_performed": 0
}
```

### ۳.۵ الگوریتم blast radius

1. Simulator cohort را با `tenant_id`، time window، action taxonomy، dataset class یا owner انتخاب می‌کند. Cohort تعریف‌شده بخشی از receiptهای immutable است؛ raw dataset را scan نمی‌کند.
2. برای هر ReceiptSnapshot، integrity receipt و EvidenceSnapshot را verify می‌کند. مورد نامعتبر در bucket جدا با `input_invalid` ثبت می‌شود و هیچ نتیجهٔ allow ایجاد نمی‌کند.
3. `baseline evaluator` با policy hash ثبت‌شده یا snapshot policy مرجع outcome را دوباره محاسبه می‌کند. اختلاف با outcome historical نشانهٔ drift engine/data-model است و simulation را `inconclusive` می‌کند.
4. `candidate evaluator` همان normalized input را با `P_new` اجرا می‌کند.
5. Diff engine transition matrix، reason-code deltas، affected action cohorts و high-impact samples را ایجاد می‌کند. نمونه‌ها فقط receipt ID/digest و metadata bounded دارند.
6. Impact classifier به policy owner می‌گوید کدام تغییر **امنیت‌افزا اما پرهزینه**، **risk-increasing** یا **neutral** است. انتقال `block → allow` یا `approval_required → allow` نیازمند Security approval مستقل است.
7. گزارش با digest policyها، cohort query digest، engine version و timestamp امضا می‌شود. اجرای واقعی فقط پس از approval report و rollout plan مجاز است.

| Transition | تفسیر پیش‌فرض | Gate لازم |
|---|---|---|
| `allow → approval_required` | اصطکاک جدید اما کنترل افزوده | owner + product workflow review |
| `allow → block` | احتمال جلوگیری از risk، اما احتمال disruption | owner + security + blast-radius threshold |
| `approval_required → block` | سخت‌گیری جدید برای caseهای قبلی | security + operations review |
| `block → approval_required` | policy relaxation محدود | security review + exception policy |
| `block/approval_required → allow` | افزایش مستقیم risk | Security sign-off، rollback plan و limited rollout |
| `inconclusive` | evidence/version لازم موجود نیست | deploy ممنوع؛ input coverage اصلاح شود |

### ۳.۶ API و storage پیشنهادی

```text
POST /v1/policies/validate
POST /v1/simulations
GET  /v1/simulations/{simulation_id}
GET  /v1/simulations/{simulation_id}/outcomes?transition=allow_to_block
POST /v1/simulations/{simulation_id}/approve-for-rollout
```

Storage v1 بهتر است relational و partitioned باشد، نه graph database:

```sql
policy_snapshots(policy_digest PK, tenant_id, policy_id, version, canonical_json, signed_at)
simulation_runs(simulation_id PK, tenant_id, baseline_policy_digest, candidate_policy_digest,
                cohort_digest, engine_version, requested_by, status, created_at)
simulation_outcomes(simulation_id, receipt_digest, baseline_outcome, candidate_outcome,
                    delta_class, reason_codes_json, PRIMARY KEY(simulation_id, receipt_digest))
```

شاخص‌ها: `(tenant_id, issued_at)` برای cohort، `(simulation_id, delta_class)` برای drill-down و `(tenant_id, policy_digest)` برای reuse. در v1 hard cap برای cohort و pagination لازم است؛ aggregation برای tenantهای بزرگ asynchronous worker می‌خواهد، اما worker فقط read-only snapshot عمل می‌کند.

### ۳.۷ Acceptance criteria برای MVP

| کنترل | معیار PASS |
|---|---|
| Determinism | اجرای یک cohort با همان snapshot و engine version، digest نتیجهٔ یکسان ایجاد کند. |
| Side effects | test double provider/outbox نشان دهد `0` call در تمام simulation paths رخ می‌دهد. |
| Version binding | تغییر یک byte در baseline/candidate policy یا evidence digest، report verification را fail کند. |
| Isolation | cohort tenant A هیچ receipt count یا sample tenant B نشان ندهد. |
| Explainability | هر delta به حداقل یک reason code و policy rule ID قابل‌نسبت‌دادن باشد. |
| Safety | `inconclusive`، policy parse error، evidence invalid یا unknown input هیچ‌گاه allow تولید نکند. |

## ۴. Evidence Graph: هدف و specification

Evidence Graph یک diagram تزئینی نیست. یک **provenance graph queryable و tamper-evident** است که از سؤال «این receipt چه چیزی را ثابت می‌کند؟» به مسیر دقیق evidence پاسخ می‌دهد.

### ۴.۱ مدل ذهنی

```text
DatasetFingerprint ──derived_to──> LineageEvent ──produced──> EvidenceBundle
       │                                      │                      │
       │                                      └──evaluated_by──> ContractVersion
       │                                                             │
       └──classified_by──> SensitivityProfile                        ▼
                                                        PolicySnapshot ──evaluated──> DecisionReceipt
                                                                                       │       │
                                                            ApprovalRecord ──approves──┘       └──authorizes──> ActionAttempt
                                                                                                                │
                                                                                                             ArtifactDigest
```

تمام nodeها با digest یا ID opaque شناسایی می‌شوند. Graph نباید dataset rows، recipient PII، local paths یا prompt متن را ذخیره کند. برای human UI، labels باید از taxonomy bounded مانند `report.html` یا `quality_gate_not_approved` تولید شوند.

### ۴.۲ Node types

| Node | کلید طبیعی | فیلدهای مجاز | منبع ایجاد | حساسیت |
|---|---|---|---|---|
| `DatasetFingerprint` | `dataset_fingerprint` | schema fingerprint، row-count range، sensitivity summary | local Trust Center | metadata-only |
| `LineageEvent` | `lineage_event_digest` | operation taxonomy، input/output fingerprints، timestamp | transformation engine | metadata-only |
| `ContractVersion` | `contract_digest` | name opaque، rule type/count، parameter fingerprints | governance engine | metadata-only |
| `QualityEvaluation` | `quality_eval_digest` | gate outcome، score bucket، reason codes | quality gate | metadata-only |
| `SchemaEvaluation` | `schema_eval_digest` | compatible/blocked، change taxonomy | schema drift guard | metadata-only |
| `EvidenceBundle` | `payload_sha256` | key ID، generated time، bundle schema | evidence core | signed metadata |
| `PolicySnapshot` | `policy_digest` | policy ID/version، rule IDs، approval digest | policy registry | signed metadata |
| `DecisionReceipt` | `payload_sha256` | receipt ID, outcome, expiry, action taxonomy | decision engine | signed metadata |
| `ApprovalRecord` | `approval_digest` | role، status، expiry، reason taxonomy | approval workflow | metadata-only |
| `ActionAttempt` | `attempt_id` | action taxonomy، executed/blocked state، receipt digest | action gate | metadata-only |
| `ArtifactDigest` | `artifact_sha256` | type، generated time، optional retention class | export/report gate | digest-only |
| `SimulationRun` | `simulation_id` | baseline/candidate policy digest، cohort digest، outcome digest | policy simulator | metadata-only |

### ۴.۳ Edge types و invariants

| Edge | From → To | invariant |
|---|---|---|
| `DERIVED_TO` | DatasetFingerprint → LineageEvent | output fingerprint event باید با input node بعدی سازگار باشد. |
| `EVALUATED_BY` | LineageEvent/DatasetFingerprint → ContractVersion | contract digest باید با evidence bundle برابر باشد. |
| `OBSERVED_AS` | ContractVersion → QualityEvaluation | quality evaluation immutable است. |
| `PACKAGED_IN` | evaluations/lineage → EvidenceBundle | bundle signature باید قبل از edge creation verify شود. |
| `EVALUATED_UNDER` | EvidenceBundle → PolicySnapshot | policy digest receipt باید با policy node برابر باشد. |
| `DECIDED_AS` | PolicySnapshot → DecisionReceipt | decision reason codes باید به rule IDs قابل‌ردیابی باشند. |
| `APPROVED_BY` | ApprovalRecord → DecisionReceipt | only approval-required receipt قابل اتصال است؛ approval نمی‌تواند evidence block را override کند. |
| `AUTHORIZES` | DecisionReceipt → ActionAttempt | receipt must be allow, unexpired و action-matched در زمان attempt. |
| `EMITS` | ActionAttempt → ArtifactDigest | only executed attempt می‌تواند artifact داشته باشد. |
| `SIMULATED_BY` | DecisionReceipt/PolicySnapshot → SimulationRun | simulation read-only و side-effect-free است. |

هر edge باید `tenant_id` مشترک، `observed_at` UTC، `producer_version` و `edge_digest` داشته باشد. Edge ناقض invariant reject می‌شود؛ graph «best effort» که بعداً inconsistent شود، برای audit قابل‌اتکا نیست.

### ۴.۴ مدل ذخیره‌سازی پیشنهادی

PostgreSQL با یک graph projection relational برای v1 توصیه می‌شود؛ زیرا tenant isolation، transactional integrity، RLS، backup و queryهای audit را با stack موجود Control Plane هم‌راستا نگه می‌دارد. graph database فقط پس از اثبات scale/query-limit باید ارزیابی شود.

```sql
CREATE TABLE evidence_graph_nodes (
  tenant_id UUID NOT NULL,
  node_digest TEXT NOT NULL,
  node_type TEXT NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL,
  metadata JSONB NOT NULL,
  producer_version TEXT NOT NULL,
  signature_status TEXT NOT NULL,
  PRIMARY KEY (tenant_id, node_digest)
);

CREATE TABLE evidence_graph_edges (
  tenant_id UUID NOT NULL,
  edge_digest TEXT NOT NULL,
  edge_type TEXT NOT NULL,
  from_digest TEXT NOT NULL,
  to_digest TEXT NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL,
  metadata JSONB NOT NULL,
  producer_version TEXT NOT NULL,
  PRIMARY KEY (tenant_id, edge_digest),
  FOREIGN KEY (tenant_id, from_digest) REFERENCES evidence_graph_nodes(tenant_id, node_digest),
  FOREIGN KEY (tenant_id, to_digest) REFERENCES evidence_graph_nodes(tenant_id, node_digest)
);

ALTER TABLE evidence_graph_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_graph_edges ENABLE ROW LEVEL SECURITY;
```

در عمل، constraints composite و policyهای RLS باید مانند schema موجود Control Plane با `app.tenant_id` enforce شوند. JSONB صرفاً metadata schema-validated نگه می‌دارد؛ query-critical fieldها باید column مستقل و indexed باشند. Edge digest از canonical JSON شامل `tenant_id`, type, endpoints, metadata hash و producer version ساخته می‌شود.

### ۴.۵ ingestion pipeline

1. Decision engine receipt و evidence bundle را local یا Control Plane صادر می‌کند.
2. `Graph Ingestor` ابتدا signature Receipt و nested Evidence Bundle را verify می‌کند؛ اعتبارسنجی پیش از persist الزامی است.
3. Node extractor با allow-list فیلدها را به node/edge candidate تبدیل می‌کند؛ local path، value، recipient و unbounded text حذف می‌شود.
4. `Invariant Validator` tenant binding، type schema، edge rules و digest equality را بررسی می‌کند.
5. Transaction builder nodeهای جدید و edgeهای لازم را atomically upsert می‌کند. receipt قابل‌verify اما graph-incomplete با status `ingestion_pending` ثبت می‌شود؛ action gate از این status برای allow استفاده نمی‌کند مگر policy صریحاً اجازه دهد.
6. `Graph Ledger` یک checkpoint digest برای batch می‌سازد تا tamper detection و reconciliation مستقل ممکن باشد.
7. Query API فقط projection tenant-scoped و redacted را بازمی‌گرداند؛ raw receipt download نیازمند permission جدا و audit event است.

### ۴.۶ queryهای محصولی که باید قبل از UI زیبا ساخته شوند

| سؤال | query graph | خروجی موردنیاز |
|---|---|---|
| «چرا این export block شد؟» | Receipt ← Policy ← Evidence ← Quality/Schema | policy rule + reason code + digest chain. |
| «کدام artifactها از dataset دچار drift تأثیر گرفتند؟» | Dataset → Lineage* → Evidence → Receipt → Action → Artifact | artifact digest، action status و receipt expiry. |
| «کدام approvalها اکنون به دلیل expiry بی‌اعتبارند؟» | Approval → Receipt → ActionAttempt | approval metadata و action counts بدون raw data. |
| «این policy change چه receipts تاریخی را تغییر می‌دهد؟» | PolicySnapshot ← SimulationRun → Receipt | transition matrix و top cohorts. |
| «آیا agent بدون proof action کرده است؟» | ActionAttempt بدون inbound `AUTHORIZES` allow edge | security incident candidate، نه verdict خودکار. |

### ۴.۷ API پیشنهادی

```text
POST /v1/evidence-graph/ingest/receipt
GET  /v1/evidence-graph/receipts/{receipt_digest}/explain
GET  /v1/evidence-graph/datasets/{fingerprint}/impact?depth=6
GET  /v1/evidence-graph/actions/unproven?from=...&to=...
GET  /v1/evidence-graph/approvals/expiring?within_seconds=86400
```

responseها باید pagination، query cost limit، `max_depth` و `max_nodes` داشته باشند. traversal بدون cap می‌تواند به DoS یا inference metadata منجر شود. برای UI، graph باید first render را به summary محدود کند و drill-down را explicit نگه دارد.

### ۴.۸ امنیت، retention و governance

| ریسک | کنترل ضروری |
|---|---|
| Graph reveals sensitive business structure | node taxonomy bounded، raw name/path/value ممنوع، role-scoped views و export audit. |
| Cross-tenant traversal | RLS در هر table، tenant binding در edge validator و integration test A/B tenant. |
| Receipt tamper | nested signature verification، canonical digest و batch checkpoint. |
| Replay of expired proof | verifier checks expiry/action match؛ graph presence هرگز authorization نیست. |
| Approval privilege escalation | approval role/action/policy digest/expiry bind می‌شود؛ approval cannot override block. |
| Unbounded growth | partition by tenant/month، retention class، archive digest checkpoints و deletion workflow auditable. |
| Graph poisoning | only signed producer identities may ingest; unknown producer is quarantined, not linked. |

## ۵. ترتیب اجرا و Definition of Done

### Policy Simulator MVP

Policy registry، deterministic evaluator، snapshot loader، delta matrix، simulation report signing، RLS، no-side-effect test و approval gate برای rollout باید در یک vertical slice تحویل شود. UI graph یا LLM copilot جزء شرط MVP نیست.

### Evidence Graph MVP

Graph Ingestor برای Decision Receipt و Evidence Bundle، relational projection، explain-receipt query، lineage impact query، tenant isolation tests، signature/reconciliation tests و read-only UI summary لازم است. Graph database، cross-company exchange و natural-language query برای بعد از pilot نگه داشته می‌شود.

### Definition of Done مشترک

| معیار | شرط پذیرش |
|---|---|
| Integrity | signature، digest، policy/evidence binding و expiry در automated tests پوشش داده شود. |
| Privacy | tests ثابت کنند raw dataset values، local path و recipient در report/graph/simulation نیست. |
| Safety | candidate policy یا graph ingest invalid هیچ allow/action effect تولید نکند. |
| Isolation | integration test نشان دهد tenant A نمی‌تواند count، node یا edge tenant B را infer کند. |
| Reproducibility | simulation report با همان snapshot و engine version digest یکسان دارد. |
| Operability | Prometheus metrics، alert thresholds، audit trail، runbook و rollback/kill switch موجود باشد. |
| Customer value | یک design partner بتواند inquiry واقعی را در کمتر از پنج دقیقه با receipt explanation پاسخ دهد. |

## References

[1] [Soda — AI for Data Quality, June 2026](https://soda.io/blog/ai-for-data-quality)

[2] [Acceldata — What “Good” Data Governance Looks Like in 2026](https://www.acceldata.io/blog/what-modern-data-governance-actually-looks-like-in-2026)

[3] [Drata — Introducing AI Agent Governance, June 2026](https://drata.com/blog/introducing-ai-agent-governance)
