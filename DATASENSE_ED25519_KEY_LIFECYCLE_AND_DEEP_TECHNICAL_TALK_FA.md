# معماری Control Plane برای چرخهٔ حیات Ed25519 و ارائهٔ فنی عمیق CAS Coordinator

**نسخه:** ۱.۰ — ۲۳ اوت ۲۰۲۶
**مرز اجرا:** طراحی برای Trust Exchange و protected staging. کلید خصوصی خارج از KMS/HSM یا signer service نگهداری نمی‌شود و این سند مجوز اعتماد خودکار به issuer جدید نیست.

## ۱. مسئلهٔ کلیدی

Trust Exchange به امضای asymmetric نیاز دارد، اما مسئله فقط جایگزینی HMAC با Ed25519 نیست. Control Plane باید بتواند ثابت کند کدام issuer، با کدام key، در چه بازه‌ای، برای چه relationship و action taxonomy مجاز به امضا بوده است؛ سپس در رخداد compromise یا revocation، اجازهٔ action جدید را در زمانی محدود قطع کند. Ed25519 برای امضا در RFC 8032 تعریف شده و RFC 8037 نمایش آن را در JOSE/JWK با `kty=OKP`، `crv=Ed25519` و `alg=EdDSA` مشخص می‌کند. [1] [2]

> **اصل معماری:** private key یک capability برای امضا است؛ public key یک claim برای verify است؛ اما trust relationship یک تصمیم حاکمیتی جداگانه است. هیچ‌کدام جای دو مورد دیگر را نمی‌گیرد.

## ۲. Control Plane پیشنهادی

```text
Policy / Approval / Security Operator
                 │
                 ▼
      Key Lifecycle API + RBAC / separation of duties
                 │
       ┌─────────┼─────────────────────────────────┐
       ▼         ▼                                 ▼
Trust Registry   KMS/HSM Signing Adapter       Lifecycle Audit Outbox
(PostgreSQL/RLS)       │                                 │
       │               ▼                                 ▼
       │       Issuer Receipt Service              Audit / Evidence Graph
       ▼
JWKS Publisher ──> signed/pinned public-key cache ──> Receiver Action Gate
       │                                                     │
       └── Revocation Coordinator ──> cache invalidation ───┼──> suppress_external
                                                             ▼
                                                     CAS Rollback Coordinator
```

| جزء | مسئولیت | control اصلی |
|---|---|---|
| **Key Lifecycle API** | درخواست create/rotate/revoke و approval workflow | RBAC، separation of duties، change ticket و audit. |
| **Trust Registry** | issuer، relationship، public key، validity و revocation status | PostgreSQL transaction، RLS و immutable key event log. |
| **KMS/HSM adapter** | ایجاد/نگهداری private key و عملیات sign | private bytes هرگز به application memory یا DB وارد نمی‌شود. |
| **JWKS Publisher** | انتشار public keyهای مجاز و metadata bounded | pinned issuer endpoint، signed manifest و cache-control محدود. |
| **Receiver Key Resolver** | resolve `(issuer,kid)` برای relationship approved | `alg/kty/crv` pinning، status/validity و environment binding. |
| **Revocation Coordinator** | تبدیل revoke key به containment | key status transaction، invalidation outbox، Action Gate suppression. |
| **CAS Rollback Coordinator** | جلوگیری از race بین permit و rollback | version + `gate_epoch` fencing، dedupe digest و state safe-only. |

## ۳. مدل داده و RLS

### ۳.۱ جدول‌های اصلی

```sql
CREATE TABLE trust_issuers (
  organization_id UUID NOT NULL,
  issuer_id TEXT NOT NULL,
  display_alias TEXT NOT NULL,
  environment TEXT NOT NULL,
  registry_state TEXT NOT NULL CHECK (registry_state IN ('pending','active','suspended','offboarded')),
  jwks_endpoint TEXT NOT NULL,
  pinned_jwks_thumbprint TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (organization_id, issuer_id)
);

CREATE TABLE trust_signing_keys (
  organization_id UUID NOT NULL,
  issuer_id TEXT NOT NULL,
  key_id TEXT NOT NULL,
  algorithm TEXT NOT NULL CHECK (algorithm = 'EdDSA'),
  key_type TEXT NOT NULL CHECK (key_type = 'OKP'),
  curve TEXT NOT NULL CHECK (curve = 'Ed25519'),
  public_key_base64url TEXT NOT NULL,
  public_key_thumbprint TEXT NOT NULL,
  kms_key_reference TEXT, -- issuer-side only; never private bytes
  status TEXT NOT NULL CHECK (status IN ('proposed','active','retiring','revoked','destroyed')),
  not_before TIMESTAMPTZ NOT NULL,
  not_after TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  revocation_reason_code TEXT,
  version BIGINT NOT NULL,
  PRIMARY KEY (organization_id, issuer_id, key_id)
);

CREATE TABLE trust_key_events (
  event_id UUID PRIMARY KEY,
  organization_id UUID NOT NULL,
  issuer_id TEXT NOT NULL,
  key_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  actor_principal_id TEXT NOT NULL,
  approval_digest TEXT,
  previous_state JSONB NOT NULL,
  target_state JSONB NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL,
  event_digest TEXT NOT NULL UNIQUE
);

CREATE TABLE trust_relationships (
  organization_id UUID NOT NULL,
  relationship_id TEXT NOT NULL,
  issuer_id TEXT NOT NULL,
  receiver_organization_id UUID NOT NULL,
  environment TEXT NOT NULL,
  allowed_action_types JSONB NOT NULL,
  max_receipt_lifetime_seconds INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','active','suspended','revoked')),
  policy_digest TEXT NOT NULL,
  version BIGINT NOT NULL,
  PRIMARY KEY (organization_id, relationship_id)
);
```

تمام tableها باید RLS داشته باشند و `organization_id` از principal trusted derivation شود، نه از request body. API عمومی هرگز `kms_key_reference`، public-key internal endpoint یا raw audit metadata حساس را نشان نمی‌دهد. JWK public output فقط `kty`, `crv`, `kid`, `use`, `key_ops`, `alg`, `x` و metadata bounded trust profile را شامل می‌شود. RFC 8037 مشخص می‌کند که public JWK Ed25519 عضو `x` را دارد و private member `d` نباید در public key representation باشد. [2]

### ۳.۲ state machine کلید

```text
PROPOSED ──dual approval──> ACTIVE ──scheduled rotation──> RETIRING ──expiry──> DESTROYED
    │                            │                                 │
    │                            └──── compromise / policy ────────┤
    └──────────── validation failure ───────────────────────────────┘
                                     ▼
                                  REVOKED
```

| حالت | امضای جدید | verify receipt قبلی | JWKS | انتقال مجاز |
|---|---:|---:|---:|---|
| `proposed` | خیر | خیر | خیر | active یا revoked |
| `active` | بله | بله | بله | retiring یا revoked |
| `retiring` | خیر برای receipt جدید exchange | بله تا پایان validity/policy | بله | revoked یا destroyed |
| `revoked` | خیر | فقط evidence تاریخی با status revoked؛ action جدید خیر | ممکن است برای status disclosure باقی بماند | destroyed پس از retention |
| `destroyed` | خیر | فقط event/metadata تاریخی | خیر | هیچ |

`retiring` با `revoked` یکسان نیست. rotation برنامه‌ریزی‌شده نباید به incident containment یا false-positive Action Gate تبدیل شود. در مقابل، `revoked` باید به‌سرعت permit جدید را متوقف کند و اگر relationship policy چنین مقرر کرده، rollback trigger R1/R2 تولید کند.

## ۴. عملیات lifecycle و separation of duties

| عملیات | initiator | approver مستقل | precondition | اثر |
|---|---|---|---|---|
| Register issuer | Trust admin | Security | ownership + endpoint pinning | issuer `pending` می‌شود. |
| Propose key | Issuer admin/KMS workflow | Security | Ed25519 public key validation | key `proposed`. |
| Activate key | Key operator | Security approver | overlap/rotation plan، test signature | key `active` و JWKS publish. |
| Retire key | Key operator | Policy owner | key successor active | issuer دیگر با آن امضا نمی‌کند. |
| Revoke key | Security incident operator | emergency two-person review پس از containment | reason code + incident ID | key `revoked`، cache invalidate، gate contain. |
| Destroy key | KMS custodian | Security + retention owner | retention/legal hold clear | private key cryptographically destroyed. |
| Re-enable relationship | Trust admin | Security + receiver owner | new key/forensic evidence | relationship separately reactivated. |

برای emergency revoke، containment نباید منتظر approval دوم بماند: Security operator می‌تواند key را به `revoked` ببرد و Action Gate را suppress کند؛ approval دوم ظرف SLA عملیاتی برای ratification، incident record و recovery لازم است. recovery هرگز به reactivating همان compromised key متکی نیست؛ key جدید و relationship reapproval لازم است.

## ۵. جریان verify در Action Gate

```text
1. Receive JWS receipt envelope.
2. Strict parse: duplicate member، size/depth، exact schema و allowed headers.
3. Resolve trust relationship using local receiver identity + relationship ID.
4. Resolve public key by (issuer, kid) only from pinned registry/JWKS cache.
5. Check: alg=EdDSA, kty=OKP, crv=Ed25519, use=sig, status, validity and environment.
6. Verify Ed25519 on exact JWS signing input.
7. Verify receipt claims: issuer/receiver/action/purpose/expiry/privacy/evidence/policy binding.
8. Check nonce replay and consume one-time execution permit with current gate_epoch.
9. Commit effect only if CAS epoch remains current; otherwise suppress.
```

Public-key refresh نباید online fetch در مسیر critical allow باشد. Action Gate با cache معتبر و relationship pinned کار می‌کند؛ unknown `kid`، registry outage یا key status ambiguity به deny/suppress یا approval-required می‌رسد. RFC 7517 نیز `kid` را selector برای key rollover توصیف می‌کند، نه basis اعتماد. [3]

## ۶. سناریوهای Revocation

### سناریوی A — Suspected private-key compromise

1. Security operator key را با CAS `active|retiring → revoked` تغییر می‌دهد و incident ID/reason code ثبت می‌کند.
2. در همان تراکنش، `trust_key_revoked` audit outbox و cache invalidation event ساخته می‌شود.
3. Receiver Action Gate key status را rejected می‌بیند؛ receipt exchange جدید با آن key `exchange_key_revoked` می‌گیرد.
4. Revocation Coordinator برای relationshipهای active event containment می‌سازد: `execution_mode=suppress_external` و circuit open outbox.
5. Graph nodeهای قبلی حذف نمی‌شوند؛ با lifecycle status `revoked_key` annotate می‌شوند.
6. issuer key جدید را در `proposed` ثبت، با dual-sign pilot و independent receiver verification فعال می‌کند.
7. Security/SRE/receiver owner recovery را بعد از forensic review، shadow replay و half-open محدود approve می‌کنند.

### سناریوی B — Planned rotation

1. key جدید `proposed`، verify test vectors و JWK thumbprint ثبت می‌شود.
2. dual approval، key جدید `active` و key قبلی `retiring` می‌شود.
3. issuer برای overlap window dual-sign می‌کند؛ receiver Ed25519 جدید را verify می‌کند ولی key قدیمی receipts legacy را طبق policy می‌پذیرد.
4. after telemetry green، issuance با key قدیمی متوقف و key قدیمی در validity end destroyed می‌شود.
5. failure در migration فقط new key path را disable می‌کند؛ هیچ fallback پنهان از Ed25519 exchange receipt به HMAC انجام نمی‌شود.

### سناریوی C — JWKS mismatch یا pin violation

اگر JWK payload با thumbprint pinned، issuer metadata یا `OKP/Ed25519/EdDSA` policy ناسازگار باشد، resolver key را ingest نمی‌کند. این وضعیت `key_registry_integrity_failure` است و Action Gate نباید key قبلی را بدون policy freshness استفاده کند. در high-risk relationship، containment اعمال می‌شود؛ در low-risk internal scope، approval-required و incident ticket ایجاد می‌شود.

### سناریوی D — Receiver offboarding

relationship ابتدا `suspended`، سپس `revoked` می‌شود. Receipt جدید از issuer—even if cryptographically valid—دیگر action را مجاز نمی‌کند. Public key issuer ممکن است برای issuerهای دیگر همچنان active باشد؛ revocation relationship-level با revocation key-level متفاوت است.

## ۷. CAS Coordinator در Control Plane

CAS Coordinator باید repository implementation مبتنی بر PostgreSQL داشته باشد. Memory implementation موجود فقط test reference است؛ production path با row-level lock، optimistic version، unique trigger digest و transactional outbox اجرا می‌شود.

### ۷.۱ API داخلی پیشنهادی

```text
POST /internal/v1/action-gate/rollback-triggers
POST /internal/v1/action-gate/permits/reserve
POST /internal/v1/action-gate/permits/{execution_key}/commit
GET  /internal/v1/trust-keys/{issuer}/{kid}/status
POST /internal/v1/trust-keys/{issuer}/{kid}/revoke
```

تمام مسیرهای داخلی با service identity/mTLS یا signature service-to-service محدود می‌شوند. webhook یا client عمومی نمی‌تواند `organization_id` و scope rollback را تعیین کند؛ server آن‌ها را از route mapping، relationship یا trusted metrics source مشتق می‌کند.

### ۷.۲ atomic rollback transaction

```sql
BEGIN;

INSERT INTO action_gate_rollback_events (
  rollback_id, organization_id, scope, trigger_evidence_digest,
  transition_status, created_at
) VALUES (:id, :tenant, :scope, :digest, 'pending', now())
ON CONFLICT (organization_id, scope, trigger_evidence_digest) DO NOTHING
RETURNING rollback_id;

-- If no row: return the existing rollback outcome. Do not execute a second transition.

SELECT version, gate_epoch, mode, execution_mode, last_known_good_policy_digest
FROM action_gate_rollout_states
WHERE organization_id = :tenant AND scope = :scope
FOR UPDATE;

UPDATE action_gate_rollout_states
SET mode = 'rollback_active',
    execution_mode = 'suppress_external',
    active_policy_digest = :last_known_good,
    version = version + 1,
    gate_epoch = gate_epoch + 1,
    updated_at = now()
WHERE organization_id = :tenant AND scope = :scope
  AND version = :expected_version
  AND gate_epoch = :expected_epoch
  AND mode IN ('shadow','limited_enforce','enforce');

INSERT INTO outbox (...) VALUES ('action_gate_rollback_activated', :bounded_metadata);
UPDATE action_gate_rollback_events SET transition_status='committed', completed_at=now()
WHERE rollback_id=:id;
COMMIT;
```

`gate_epoch` یک fencing token است. preflight permit با epoch N صادر می‌شود. اگر rollback state را به N+1 ببرد، commit permit N حتی در صورتی که receipt یا signature معتبر باشد رد می‌شود. این کنترل TOCTOU بین «اجازه در لحظهٔ اول» و «اثر خارجی در لحظهٔ بعد» را می‌بندد.

## ۸. متریک، alert و evidence

| signal | labelهای مجاز | واکنش |
|---|---|---|
| `trust_exchange_verifications_total` | `outcome`, `algorithm` | invalid/revoked spike → security review. |
| `trust_key_lifecycle_events_total` | `event_type`, `status` | audit و rotation health. |
| `action_gate_rollbacks_total` | `trigger_type`, `outcome` | containment / CAS contention. |
| `action_gate_permit_rejections_total` | `reason_code` | stale epoch، replay، expiry. |
| `trust_jwks_refresh_total` | `outcome` | pin mismatch / stale cache handling. |

هیچ label شامل tenant ID، issuer URL، `kid`، receipt digest، dataset ID یا raw reason text نیست. Evidence card باید commit/image digest، relationship ID alias، old/new key thumbprint، key status transition، policy digest، rollback ID، epoch before/after، synthetic effect count و approval references را ثبت کند.

## ۹. محتوای ارائهٔ فنی عمیق

### Slide A — چرا asymmetric exchange؟

**محتوای بصری:** دو trust boundary؛ HMAC local در سمت چپ و issuer/private key + receiver/public key در سمت راست.
**متن سخنرانی:** «در داخل یک trust boundary، HMAC ساده و مفید است. اما در exchange، دادن secret به verifier یعنی دادن توان امضا به او. Ed25519 این مرز را جدا می‌کند: issuer امضا می‌کند و receiver فقط verify می‌کند. با این حال، کلید عمومی به معنای issuer مورداعتماد نیست؛ relationship و policy آن را تعیین می‌کنند.»

### Slide B — Key lifecycle Control Plane

**محتوای بصری:** state machine `proposed → active → retiring → destroyed` و branch `revoked`.
**متن سخنرانی:** «کلید فقط یک blob crypto نیست؛ asset دارای owner، validity، approval و incident history است. مهم‌ترین تمایز retiring و revoked است: rotation برنامه‌ریزی‌شده نباید workflow را متوقف کند، اما compromise باید اجازهٔ جدید را فوراً قطع کند.»

### Slide C — Trust Exchange verification path

**محتوای بصری:** JWS envelope → pinned relationship/JWKS → Ed25519 verify → claims/evidence binding → nonce/permit.
**متن سخنرانی:** «ما signature را در isolation قبول نمی‌کنیم. verifier ابتدا issuer relationship، environment، action taxonomy و key status را چک می‌کند؛ سپس Ed25519 را روی exact signing input verify می‌کند. در انتها، local Action Gate خودش execution key می‌سازد. issuer هرگز capability برای سیستم receiver صادر نمی‌کند.»

### Slide D — CAS Coordinator race condition

**محتوای بصری:** دو مسیر هم‌زمان: permit epoch 11 و rollback epoch 12؛ commit permit به fence برخورد می‌کند.
**متن سخنرانی:** «مشکل ما فقط دو trigger هم‌زمان نیست. خطر واقعی زمانی است که permit درست پیش از rollback صادر شده باشد. gate epoch به permit و rollout state bind می‌شود. rollback epoch را افزایش می‌دهد؛ بنابراین effect قدیمی حتی اگر signature معتبر داشته باشد، commit نمی‌شود.»

### Slide E — Revocation incident choreography

**محتوای بصری:** revoke event → registry update → cache invalidation → suppress external → circuit open → forensic graph.
**متن سخنرانی:** «revocation باید یک workflow خودکار containment بسازد، نه فقط تغییر یک row در database. DB state اول authoritative می‌شود؛ outbox سپس circuit و cache distribution را انجام می‌دهد. اگر outbox delayed شود، Action Gate همچنان suppress است. evidence قدیمی حذف نمی‌شود؛ status آن برای audit تغییر می‌کند.»

### Slide F — سرمایه‌گذاری و معیار تصمیم

**محتوای بصری:** جدول منافع/هزینه‌ها و Go/Narrow/Pivot/Stop.
**متن سخنرانی:** «ارزش اقتصادی این architecture در یک feature نیست؛ در کاهش bypass، کاهش زمان audit inquiry و امکان همکاری میان سازمان‌هاست. اما این thesis باید با design partner، independent verification و workflow واقعی ثابت شود. اگر receiver مستقل ارزش proof را نبیند، platform scale نمی‌شود—even if cryptography perfect باشد.»

## References

[1] [RFC 8032 — Edwards-Curve Digital Signature Algorithm (EdDSA)](https://www.rfc-editor.org/rfc/rfc8032.html)

[2] [RFC 8037 — Ed25519/Ed448 in JOSE](https://www.rfc-editor.org/rfc/rfc8037.html)

[3] [RFC 7517 — JSON Web Key (JWK)](https://www.rfc-editor.org/rfc/rfc7517.html)
