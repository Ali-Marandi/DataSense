# Policy Grammar، اجرای آزمایشی و Action Gate واقعی برای DataSense

**نسخه:** ۱.۰ — ۲۳ اوت ۲۰۲۶
**وضعیت:** specification اجرای محدود در `protected staging`؛ این سند مجوز فعال‌سازی provider واقعی یا production enforcement نیست.

## ۱. نقطهٔ شروع و مرز ادعا

DataSense هم‌اکنون Decision Receipt امضاشده، Quality Gate، Schema Drift Guard، lineage metadata و Control Plane دارای RBAC، RLS، Outbox Worker، circuit و execution ledger دارد. اما **Receipt v1 هنوز Action Gate enforcement برای export/report را اجرا نمی‌کند**؛ Trust Center فقط receipt ایجاد می‌کند. در سمت worker، policy evaluator درست پس از claim و پیش از provider call قرار گرفته است. این دو مسیر باید تحت یک Policy Grammar و یک decision contract متحد شوند، بدون اینکه desktop local-first یا fail-closed بودن delivery آسیب ببیند.

> **اصل migration:** ابتدا observe، سپس shadow decision، بعد enforcement محدود با fake sink و tenant مصنوعی. هیچ policy جدید نباید در همان release به enforce-mode برای action خارجی برود.

## ۲. Policy Grammar اجرایی

### ۲.۱ چرا DSL محدود لازم است

Policy نباید Python، SQL آزاد یا prompt طبیعی باشد. هرکدام می‌توانند non-determinism، injection، دسترسی ناخواسته به data یا رفتار غیرقابل‌audit ایجاد کنند. v1 باید **declarative، schema-validated، versioned و side-effect-free** باشد. AI Copilot در نسخه‌های آینده فقط می‌تواند draft پیشنهاد دهد؛ قبل از استفاده، draft باید توسط parser به AST محدود تبدیل، در simulator replay، و توسط owner تأیید شود.

### ۲.۲ شکل canonical policy document

```yaml
schema: datasense.policy/v1
policy_id: external-export-restricted
version: 2026.09.0
status: candidate              # candidate | approved | active | retired
scope:
  action_types:
    - export.csv
    - export.xlsx
    - report.html
  risks:
    - internal
    - external
    - autonomous
rules:
  - id: quality-must-be-approved
    when:
      field: quality_gate.decision
      operator: equals
      value: approved
      negate: true
    outcome: block
    reason_code: quality_gate_not_approved

  - id: block-prohibited-schema-drift
    when:
      field: schema_drift.decision
      operator: equals
      value: blocked
    outcome: block
    reason_code: schema_drift_blocked

  - id: approval-for-external-or-autonomous
    when:
      field: action.risk
      operator: in
      values: [external, autonomous]
    outcome: approval_required
    reason_code: action_risk_requires_approval

  - id: receipt-must-be-fresh
    when:
      field: receipt.age_seconds
      operator: greater_than
      value: 900
    outcome: block
    reason_code: receipt_expired
metadata:
  owner_principal_id: opaque-owner-id
  change_ticket: GOV-2026-091
  data_classification: internal
  reviewed_at: 2026-09-01T00:00:00Z
  expires_at: 2026-12-01T00:00:00Z
```

`policy_digest = SHA-256(canonical JSON document)` است. YAML تنها فرمت authoring است؛ registry باید YAML را parse کند، schema validate کند، به JSON canonical تبدیل کند و سپس hash/signature بسازد. هیچ rule از روی متن YAML خام اجرا نمی‌شود.

### ۲.۳ grammar مجاز

| عنصر | قاعده | دلیل امنیتی |
|---|---|---|
| `policy_id` | lower-case slug، ۳ تا ۱۲۸ کاراکتر | namespace bounded و قابل‌index. |
| `version` | semver یا تاریخ versioned؛ immutable بعد از approval | replay و rollback قطعی. |
| `status` | `candidate`, `approved`, `active`, `retired` | lifecycle صریح و audit-friendly. |
| `scope.action_types` | allow-list taxonomy مانند `export.csv` یا `agent.external_action` | جلوگیری از wildcard غیرقابل‌audit. |
| `field` | فقط allow-list context paths | عدم دسترسی policy به raw dataset یا identity حساس. |
| `operator` | `equals`, `in`, `greater_than`, `less_than`, `exists` | AST کوچک، deterministic و قابل‌test. |
| `value/values` | scalar bounded یا enum allow-listed | عدم اجرای expression یا regex آزاد در v1. |
| `outcome` | `block`, `approval_required`, `allow` | ترتیب dominance مشخص. |
| `reason_code` | allow-list ۳ تا ۶۴ کاراکتر | telemetry و audit بدون cardinality explosion. |
| metadata | owner opaque، ticket، timestamps، digest approval | accountability بدون PII یا free-text خطرناک. |

### ۲.۴ context قابل‌مشاهدهٔ policy

Policy evaluator تنها یک `DecisionContext` metadata-only دریافت می‌کند. این context باید از Receipt معتبر و Control Plane state ساخته شود، نه از request body اعتماد نشده.

```json
{
  "tenant_id": "opaque-tenant-uuid",
  "actor": {"kind": "desktop|service|agent", "role_set_digest": "sha256:..."},
  "action": {"type": "export.csv", "risk": "external", "purpose_code": "external_share"},
  "receipt": {"digest": "sha256:...", "valid": true, "age_seconds": 42, "expires_in_seconds": 858},
  "quality_gate": {"decision": "approved"},
  "schema_drift": {"decision": "compatible"},
  "lineage": {"digest": "sha256:...", "event_count": 4},
  "sensitivity": {"highest_class": "restricted", "summary_digest": "sha256:..."},
  "approval": {"state": "not_required|valid|missing|expired|revoked", "digest": null},
  "environment": "staging"
}
```

Context دارای dataset row، value، path محلی، recipient، URL، prompt، credential یا email نیست. اگر یک field لازم unavailable یا signature Receipt نامعتبر باشد، evaluator باید `block` با `policy_input_unknown` یا `receipt_invalid` بدهد.

### ۲.۵ semantics و precedence

1. Parser policy را به AST immutable تبدیل می‌کند؛ AST فقط nodeهای allow-listed دارد.
2. Evaluator ابتدا integrity Receipt، expiry، action-scope، tenant binding و policy status را بررسی می‌کند.
3. سپس ruleهای `block` را evaluate می‌کند؛ نخستین match یا مجموعهٔ matchها outcome را `block` می‌سازند.
4. فقط اگر blockی match نشد، `approval_required` بررسی می‌شود.
5. `allow` فقط با inputs کامل، policy active و match explicit یا default policy allow ممکن است. Unknown هیچ‌گاه allow نیست.
6. approval فقط یک `approval_required` معتبر را کامل می‌کند و هرگز `block` ناشی از quality، schema، signature یا kill switch را override نمی‌کند.
7. نتیجه شامل `outcome`, `reason_codes`, `matched_rule_ids`, `policy_digest`, `context_digest`, `engine_version` و `evaluated_at` است.

```python
# Pseudocode: نه eval()، نه dynamic import، نه side effect
for rule in policy.rules_by_precedence():
    if ast_match(rule.when, trusted_context):
        matched.append(rule)

if any(rule.outcome == "block" for rule in matched):
    return Decision("block", reasons(matched), ...)
if any(rule.outcome == "approval_required" for rule in matched):
    return Decision("approval_required", reasons(matched), ...)
return Decision("allow", ["all_trust_gates_satisfied"], ...)
```

### ۲.۶ lifecycle و approval policy

| وضعیت | چه کسی مجاز است | خروجی | action مجاز؟ |
|---|---|---|---|
| Draft | policy author | schema validation فقط | خیر |
| Candidate | policy owner | simulation report | خیر |
| Approved | Data Governance + Security در policyهای relax‌کننده | immutable signed snapshot | خیر، مگر release promotion مستقل |
| Active in Shadow | SRE/Platform | decision log فقط | خیر؛ gate allow/block enforce نمی‌کند |
| Active Limited Enforce | Change approver + Security | receipt/gate enforcement برای tenant synthetic یا allow-listed | فقط scope مصوب |
| Retired | policy owner | historical replay حفظ می‌شود | خیر |

`block → allow` یا `approval_required → allow` در blast-radius report یک **relaxation** است و به Security sign-off، rollback plan و limited rollout نیاز دارد. `allow → block` نیز اگر threshold impact بالاتر از SLO باشد، نیازمند operations approval دارد.

## ۳. معماری و API Policy Registry / Evaluator

### ۳.۱ اجزای پیشنهادی

```text
Git-signed policy source / UI draft
                │
                ▼
  Policy Validator ──► Canonicalizer ──► Policy Registry (PostgreSQL)
                │                                   │
                ▼                                   ▼
          Static checks                       Immutable PolicySnapshot
                │                                   │
                └──────────► Policy Simulator ◄─────┘
                                              │
                           approved snapshot  ▼
Desktop / API / Worker ──► Action Gate ──► Deterministic Evaluator
                                              │
                                              ▼
                              Signed Decision Receipt + Evidence Graph ingest
```

### ۳.۲ endpointهای Control Plane

| Endpoint | Permission پیشنهادی | وظیفه |
|---|---|---|
| `POST /v1/policies/validate` | `POLICY_WRITE` | schema/AST/static validation؛ persist نمی‌کند. |
| `POST /v1/policies` | `POLICY_WRITE` | candidate immutable snapshot می‌سازد. |
| `POST /v1/policies/{digest}/simulate` | `POLICY_SIMULATE` | job read-only با cohort bounded می‌سازد. |
| `POST /v1/policies/{digest}/approve` | `POLICY_APPROVE` | signed approval با separation-of-duty ثبت می‌کند. |
| `POST /v1/actions/preflight` | `ACTION_REQUEST` | Receipt/evidence/action را verify و outcome امضاشده می‌دهد. |
| `POST /internal/v1/actions/enforce` | service identity only | مسیر worker/gateway؛ public route نیست. |
| `GET /v1/receipts/{digest}/explain` | `EVIDENCE_READ` | explanation redacted و tenant-scoped. |

در FastAPI، این dependencies به `ControlPlaneComponents` افزوده می‌شوند، همانند `quality_gate_service` و `activation_alert_controller`. `PermissionMiddleware` باید endpointهای public/internal را جدا نگه دارد؛ internal endpoint با mTLS یا signed service identity و NetworkPolicy محدود می‌شود، نه JWT کاربر نهایی.

## ۴. اجرای آزمایشی روی کلاستر pilot

### ۴.۱ posture فعلی و پیش‌شرط‌ها

overlay فعلی staging در namespace `datasense-control-plane-staging` قرار دارد و outbox worker را عمداً روی `0` replica نگه می‌دارد تا migration، fake-sink acceptance، queue recovery و alert-routing با تصمیم امضاشده انجام شود. این guard باید حفظ شود؛ Policy Simulator هیچ دلیل فنی برای فعال‌سازی worker یا provider واقعی نیست.

| پیش‌شرط | مدرک لازم | blocking condition |
|---|---|---|
| namespace ایزوله | `datasense-control-plane-pilot` یا staging tenant sandbox | استفاده از namespace production یا shared credentials. |
| synthetic tenant | tenant و dataset fingerprint ساختگی، owner مشخص | receipt یا evidence واقعی مشتری وارد pilot شود. |
| image immutable | digest GHCR، SBOM/provenance، CI success | tag شناور مانند `latest`. |
| database/Redis sandbox | URL و secret جدا، retention کوتاه | اشتراک DB/Redis production. |
| fake sink | receiver local/mock که effect count را ثبت می‌کند | webhook/provider واقعی یا credential واقعی. |
| observability | Prometheus scrape، dashboard، alert route non-paging یا test route | metric/alert بدون owner. |
| change approval | Security + SRE + Data Governance sign-off | اجرای direct apply بدون ticket. |

### ۴.۲ resourceهای Kubernetes پیشنهادی

| Resource | نام پیشنهادی | role | guard |
|---|---|---|---|
| Deployment | `datasense-policy-simulator` | replay read-only، یک replica | service account مستقل، read-only FS، no provider env. |
| Deployment | `datasense-action-gate` | preflight/enforce API | HPA بعد از load test، readiness وابسته به policy registry. |
| ConfigMap | `datasense-policy-simulator-config` | limits، cohort cap، mode `shadow` | policy content حساس در ConfigMap نگهداری نمی‌شود. |
| Secret | `datasense-action-gate-secrets` | key reference/mTLS/client secrets | external secret manager یا sealed secret؛ never commit. |
| ServiceAccount | `datasense-policy-simulator` | least-privilege identity | هیچ permission برای jobs/deployments/secrets list. |
| NetworkPolicy | `allow-policy-read-only` | egress فقط PostgreSQL/Redis/DNS و ingress فقط gateway/monitoring | default deny باقی می‌ماند. |
| ServiceMonitor | `datasense-policy-simulator` | metrics scrape | namespaceSelector محدود به pilot. |
| PDB/HPA | پس از game day | availability نه release authorization | HPA نمی‌تواند mode را از shadow به enforce تغییر دهد. |

پیکربندی non-secret نمونه:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: datasense-policy-simulator-config
data:
  DATASENSE_ENVIRONMENT: staging
  POLICY_SIMULATION_MODE: shadow
  POLICY_SIMULATION_MAX_COHORT: "5000"
  POLICY_SIMULATION_MAX_DEPTH: "6"
  POLICY_SIMULATION_RETENTION_HOURS: "168"
  ACTION_GATE_DEFAULT_OUTCOME: block
  ACTION_GATE_ALLOW_PROVIDER_CALLS: "false"
```

`ACTION_GATE_ALLOW_PROVIDER_CALLS` باید در pilot `false` باقی بماند. تغییر آن نباید صرفاً با ConfigMap rollout انجام شود؛ باید admission/promotion control، approval artifact و second-person review داشته باشد.

### ۴.۳ مراحل عملی rollout

| گام | عمل | evidence / exit criterion |
|---|---|---|
| P0 — Render | `kubectl kustomize` و schema validation روی overlay pilot؛ بدون apply | rendered manifest، image digest، NetworkPolicy diff. |
| P1 — Preflight | secret references، RLS migration، service account و readiness dependency verify | migration checksum، secret mount check، health endpoint 200. |
| P2 — Shadow simulator | simulator با cohort synthetic و `side_effects=0` اجرا شود | simulation report signed، provider/outbox calls = 0. |
| P3 — Shadow Action Gate | desktop/CLI/API preflight call outcome تولید کند، ولی action را متوقف نکند | decision telemetry، zero false labeling، no provider traffic. |
| P4 — Fake-sink enforce | فقط action taxonomy allow-listed، tenant synthetic و fake sink؛ outbox worker هنوز provider واقعی ندارد | count attempt/allow/block برابر، execution ledger idempotency pass. |
| P5 — Limited enforcement | بعد از Security/SRE approval، یک workflow کم‌خطر non-production | rollback drill، RTO/RPO evidence، alert acknowledgement. |
| P6 — Gate review | Go/Narrow/Pivot/Stop | evidence card کامل و signed decision. |

### ۴.۴ دستورهای نمونهٔ غیرمخرب

```bash
# فقط render و validate محلی؛ apply یا mutation انجام نمی‌دهد
kubectl kustomize enterprise_control_plane/k8s/overlays/staging > /tmp/datasense-staging.yaml
kubectl apply --dry-run=server -f /tmp/datasense-staging.yaml

# وضعیت deployment و readiness پس از approval change
kubectl -n datasense-control-plane-staging get deploy,pod,svc
kubectl -n datasense-control-plane-staging rollout status deploy/datasense-policy-simulator

# صرفاً مشاهدهٔ policy/traffic؛ نه secret و نه event payload
kubectl -n datasense-control-plane-staging logs deploy/datasense-policy-simulator --since=10m
```

این دستورها فقط بعد از انتخاب context صحیح و تأیید change owner باید اجرا شوند. هیچ‌کدام نباید در CI عادی production اجرا شوند.

### ۴.۵ SLO، متریک و rollback

| Signal | threshold محدود production-like | واکنش |
|---|---:|---|
| `policy_evaluation_errors_total` | هر خطای unknown input در enforcement | mode به `shadow`، action block fail-closed، ticket incident. |
| `policy_simulation_side_effects_total` | باید `0` باشد | immediate stop؛ incident security. |
| `action_gate_decisions_total{outcome}` | shift بیشتر از baseline تعریف‌شده | freeze promotion و review blast radius. |
| `action_gate_latency_seconds` p95 | threshold توافق‌شده در pilot، مانند 250ms داخلی | bypass ممنوع؛ scale/readiness review. |
| `receipt_verification_failures_total` | هر spike غیرمنتظره | key/clock/policy rollback review. |
| `graph_ingestion_quarantine_total` | spike نسبت به baseline | producer isolate، action allow جدید صادر نشود. |

Rollback باید کم‌خطر باشد: `enforce → shadow` برای scope مصوب، scale worker/simulator به صفر در صورت defect بحرانی، revoke policy activation و restore previous immutable policy digest. Rollback **نباید** با حذف receipt یا audit event انجام شود.

## ۵. Action Gate واقعی: طراحی و مسیر یکپارچه‌سازی

### ۵.۱ contract واحد Action Gate

Action Gate تنها نقطه‌ای است که می‌تواند اجازهٔ effect خارجی بدهد. همهٔ adapterها—desktop export، report/dashboard export، CLI، API، MCP agent و Outbox Worker—باید این contract را پیش از effect صدا بزنند.

```text
ActionIntent + Signed Evidence Bundle + actor/service identity
                          │
                          ▼
                 Verify signature, expiry, tenant, scope
                          │
                          ▼
                  Policy evaluator + approval lookup
                          │
              ┌───────────┼────────────┐
              ▼           ▼            ▼
            BLOCK      APPROVAL      ALLOW
              │       REQUIRED         │
              ▼           ▼            ▼
     no effect + receipt   no effect + approval request    single guarded effect
```

`ALLOW` پاسخ باید شامل `decision_receipt_digest`، `policy_digest`، `expires_at`، `action_nonce` و `execution_key` باشد. downstream adapter پیش از effect باید `execution_key` را در ledger reserve کند. این اتصال همان تضمین موجود execution ledger را از outbox به همهٔ actionها گسترش می‌دهد.

### ۵.۲ interface پیشنهادی

```python
@dataclass(frozen=True)
class ActionRequest:
    tenant_id: str
    actor_id: str                # opaque ID, derived from JWT/service identity
    action: ActionIntent
    evidence_bundle: Mapping[str, Any]
    artifact_digest: str | None  # hash of a staged artifact, never path/value
    idempotency_key: str

@dataclass(frozen=True)
class GateDecision:
    outcome: Literal["allow", "approval_required", "block"]
    receipt: Mapping[str, Any]
    policy_digest: str
    execution_key: str | None
    reason_codes: tuple[str, ...]
```

```python
async def authorize_action(request: ActionRequest) -> GateDecision:
    # 1) identity/RBAC and tenant binding
    # 2) validate canonical evidence signature, expiry and privacy flags
    # 3) load immutable active PolicySnapshot
    # 4) evaluate deterministic AST and approval state
    # 5) issue a signed Decision Receipt for ALL outcomes
    # 6) reserve execution ledger key only if outcome == allow
    # 7) append audit/evidence graph metadata; fail closed if required dependency unavailable
```

### ۵.۳ مسیرهای یکپارچه‌سازی

| ابزار موجود | integration point | behavior در v1 | protection مهم |
|---|---|---|---|
| Trust Center desktop | قبل از `DataManager.export` و export report/dashboard | ابتدا shadow/preflight و Receipt sidecar؛ سپس enforce برای external exports | artifact ابتدا در temp staging، digest سپس gate، final rename فقط پس از allow. |
| Signed Evidence Bundle | input اجباری Gate | nested evidence signature/quality/schema/lineage verify | raw data هرگز در request نیست. |
| Outbox Worker | existing `policy_evaluator` پیش از `WebhookDeliveryClient` | Policy Grammar adapter جای `DeliveryEligibilityService` یا با آن compose می‌شود | kill switch/consent/circuit همچنان mandatory و block-dominant. |
| Execution Ledger | بعد از allow و پیش از effect | idempotency/execution key reserve + completion/unknown recovery | crash نباید external effect را duplicate کند. |
| Control Plane RBAC | preflight/API gateway | permission `ACTION_REQUEST` و service identity scope | tenant ID از principal، نه request body. |
| Kubernetes / NetworkPolicy | API/worker isolation | only Action Gate service can reach fake/real sink after promotion | simulator/desktop relay مستقیم provider را نمی‌بیند. |
| AI agent MCP/CLI | tool wrapper قبل از outbound tool call | agent receives proof or bounded denial | agent cannot supply self-signed evidence. |

### ۵.۴ Desktop export transaction

برای جلوگیری از ایجاد artifact نهایی قبل از decision، export desktop باید از الگوی stage/gate/commit استفاده کند:

1. DataManager artifact را در directory موقت محلی با نام opaque می‌سازد.
2. فقط `artifact_sha256`، action type و Receipt/evidence metadata برای Gate فرستاده می‌شود.
3. اگر `block` یا `approval_required` باشد، temp artifact securely deleted یا quarantined می‌شود؛ destination final نوشته نمی‌شود.
4. اگر `allow` باشد، execution key محلی/enterprise reserve می‌شود، artifact atomically به destination rename می‌شود و receipt sidecar کنار آن نوشته می‌شود.
5. completion event شامل digest و receipt digest به ledger/graph append می‌شود؛ failure بعد از rename به `unknown` می‌رود و recovery فقط با idempotency contract انجام می‌شود.

در local-only mode، Gate engine embedded و local key store استفاده می‌کند؛ در enterprise mode، preflight و approval از Control Plane می‌آید. semantics allow/block باید در هر دو mode یکسان باشد.

### ۵.۵ Outbox delivery transaction

مسیر worker پیشاپیش نزدیک‌ترین نمونهٔ واقعی Gate است: event claim می‌شود، `DeliveryEligibilityService` consent/kill switch/circuit را درست پیش از provider call بررسی می‌کند، سپس execution ledger جلوی effect تکراری را می‌گیرد. Policy Grammar باید به‌صورت compose اضافه شود:

```text
Claimed event
   → tenant / RLS assertion
   → consent + tenant kill switch + circuit check
   → verify evidence + policy action evaluation
   → reserve execution ledger
   → fake/approved provider call
   → mark effect / ack OR suppress / retry / DLQ
```

هر dependency unavailable باید `suppressed_dependency_unavailable` یا retry-controlled ایجاد کند؛ provider call بدون verdict قطعی ممنوع است.

### ۵.۶ rollout Action Gate

| مرحله | scope | enforcement | معیار خروج |
|---|---|---|---|
| Observe | internal report/export | log current decision only | reason coverage و latency baseline. |
| Shadow | synthetic + selected pilot workflows | compare decision، no block | mismatch investigation کامل. |
| Soft gate | external export synthetic | UI requires acknowledgement، no real sink | approval UX و receipt verification. |
| Hard gate fake sink | synthetic tenant | `allow` تنها مسیر effect | 0 bypass و 0 duplicate effect. |
| Limited enforce | 1 allow-listed workflow، signed change | block/approval واقعی در scoped environment | Security + SRE evidence card. |
| Broaden | cohort به cohort | policy promotion controlled | SLO، false-positive و rollback criteria. |

### ۵.۷ آزمون‌های پذیرش ضروری

| سناریو | assertion |
|---|---|
| Receipt tampered/expired/action mismatch | final artifact/provider effect = 0. |
| Quality Gate fail یا schema block | `block` precedence دارد؛ approval نمی‌تواند override کند. |
| External action با evidence معتبر | `approval_required`؛ receipt allow صادر نمی‌شود. |
| Consent revoked بعد از claim | provider call = 0؛ final status suppressed. |
| Circuit open یا tenant kill switch | action blocked/suppressed tenant-scoped. |
| Crash پس از allow پیش از completion | ledger prevents uncontrolled duplicate effect. |
| RLS A/B tenant | tenant A هیچ evidence/decision B را نمی‌بیند. |
| Simulator policy candidate | provider/outbox call = 0 و report reproducible. |
| Graph ingestion unavailable | dependency policy مطابق config: block یا safe retry؛ no silent allow. |

## ۶. تصمیم‌های لازم قبل از نوشتن کد enforcement

1. انتخاب یک design partner با workflow کم‌خطر و dataset کاملاً synthetic برای pilot.
2. مشخص‌کردن owner برای Policy، Security، SRE و Privacy؛ separation of duties اجباری است.
3. تعریف taxonomy اولیهٔ ۶ تا ۱۰ action و ۱۲ تا ۲۰ reason code؛ گسترش آزاد ممنوع.
4. توافق بر SLO latency، retention، cohort cap و thresholds blast radius.
5. آماده‌سازی fake sink، rollback drill و evidence card قبل از تغییر replica worker یا خروجی provider.
6. انتخاب مدل key management برای production؛ HMAC local v1 برای desktop مناسب است، اما cross-organization exchange باید به key discovery/rotation و احتمالاً asymmetric signing مهاجرت کند.

## References

[1] [Soda — AI for Data Quality, June 2026](https://soda.io/blog/ai-for-data-quality)

[2] [Acceldata — What “Good” Data Governance Looks Like in 2026](https://www.acceldata.io/blog/what-modern-data-governance-actually-looks-like-in-2026)

[3] [Drata — Introducing AI Agent Governance, June 2026](https://drata.com/blog/introducing-ai-agent-governance)
