# مهاجرت Ed25519، Trust Exchange و CAS Coordinator برای Automatic Rollback

**نسخه:** ۱.۰ — ۲۳ اوت ۲۰۲۶
**وضعیت:** طراحی اجرای محدود و تست‌شده برای protected staging؛ این سند مجوز انتشار کلید خصوصی، trust خودکار issuer جدید یا action خارجی بدون approval نیست.

## ۱. تصمیم معماری

DataSense در نسخهٔ محلی و داخل یک سازمان می‌تواند HMAC-SHA256 را برای Signed Evidence Bundle و Decision Receipt نگه دارد؛ signer و verifier هر دو در یک trust boundary مشترک‌اند. اما در Trust Exchange بین‌سازمانی، verifier نباید secret signer را داشته باشد. بنابراین signatureهای exchange باید به **Ed25519** منتقل شوند و verifier فقط public key را از یک issuer registry مورداعتماد دریافت کند. Ed25519 در RFC 8032 تعریف شده و RFC 8037 استفادهٔ Ed25519 در JOSE/JWK را با key type `OKP` و curve `Ed25519` استاندارد می‌کند. [1] [2]

> **مرز مهم:** Ed25519 قابلیت trust ایجاد نمی‌کند. فقط نشان می‌دهد holder کلید خصوصی، payload معینی را امضا کرده است. Trust Exchange باید جداگانه issuer، tenant binding، endpoint discovery، key status و relationship هر طرف را establish کند.

## ۲. مدل Trust Exchange

### ۲.۱ نقش‌ها و trust boundary

| نقش | مسئولیت | هیچ‌گاه نباید انجام دهد |
|---|---|---|
| Issuer Organization | receipt/evidence را با کلید خصوصی Ed25519 امضا می‌کند | کلید خصوصی را در receipt، JWK یا log منتشر کند |
| Issuer Registry | public key، status و validity interval را با governance منتشر می‌کند | trust سازمان جدید را صرفاً با DNS یا self-assertion فعال کند |
| Receiver Organization | receipt را با public key pinned یا registry-approved verify می‌کند | به `kid` بدون issuer/trust relationship اعتماد کند |
| Trust Exchange Broker | onboarding، policy relationship، audit و metadata discovery را تسهیل می‌کند | به‌جای Receiver، action authorization صادر کند |
| Action Gate | receipt/issuer/action/tenant/expiry را verify و execution key reserve می‌کند | graph presence یا signature به‌تنهایی را `allow` بداند |

هر relationship به یک `trust_relationship_id` immutable متصل می‌شود. relationship شامل issuer ID، receiver ID، approved action taxonomy، environment، key-use policy، maximum receipt lifetime، privacy profile و revocation behavior است. `issuer` یک string نمایشی نیست؛ یک identity registry record با onboarding approval است.

### ۲.۲ public key representation

JWK عمومی Ed25519 باید حداقل با این قالب سازگار باشد. RFC 8037 برای EdDSA از `kty=OKP`، `crv=Ed25519` و public member `x` base64url استفاده می‌کند؛ private member `d` هرگز در key set عمومی وجود ندارد. [2]

```json
{
  "kty": "OKP",
  "crv": "Ed25519",
  "kid": "org-acme-sign-2026-09",
  "use": "sig",
  "key_ops": ["verify"],
  "alg": "EdDSA",
  "x": "base64url-ed25519-public-key",
  "datasense_issuer": "urn:datasense:issuer:acme",
  "datasense_status": "active",
  "datasense_not_before": "2026-09-01T00:00:00Z",
  "datasense_not_after": "2027-09-01T00:00:00Z"
}
```

`kid` فقط selector است، نه trust assertion. Key resolver باید جفت `(issuer, kid)` را با relationship، environment، key type/curve/algorithm، validity interval و status بررسی کند. RFC 7517 نیز JWK Set را یک object با member `keys` تعریف می‌کند و برای key rollover، `kid` را key selector می‌داند. [3]

### ۲.۳ discovery و onboarding

1. issuer درخواست onboarding می‌دهد و مالکیت domain/organization خارج از receipt تأیید می‌شود.
2. Security administrator receiver، issuer registry URL و public-key thumbprint اولیه را **pinned** می‌کند.
3. Trust Exchange یک relationship approval با scope محدود می‌سازد: مثلاً فقط `report.html` در `staging` و `external` risk ممنوع.
4. Receiver JWKS را فقط از HTTPS endpoint allow-listed، با TLS validation و cache TTL bounded دریافت می‌کند. Redirect cross-origin، URL داخل receipt و dynamic endpoint discovery بدون approval ممنوع است.
5. هر JWKS update با schema validation، duplicate key rejection، issuer binding، algorithm allow-list و trust registry check وارد cache می‌شود.
6. به‌روزرسانی key set در audit trail ثبت می‌شود؛ key ناشناخته به on-demand fetch نامحدود یا fallback HMAC منجر نمی‌شود.

نمونه endpoint:

```text
GET https://issuer.example/.well-known/datasense-trust/jwks.json
GET https://issuer.example/.well-known/datasense-trust/issuer-metadata.json
```

receiver برای issuerهای high-risk می‌تواند endpoint را از configuration داخلی resolve کند و نه از URL در receipt. اگر registry unavailable باشد، action جدید external `block` یا `approval_required` می‌شود؛ receipt قدیمی به allow offline تبدیل نمی‌شود مگر policy صریح و key cache هنوز معتبر باشد.

## ۳. Signature envelope و قرارداد Ed25519

### ۳.۱ انتخاب serialization

در v1 داخلی، payload canonical JSON مستقیم امضا می‌شود. برای Trust Exchange باید **JWS JSON Serialization با protected header** یا یک envelope معادل دقیق و versioned انتخاب شود. این سند JWS JSON Serialization را برای interoperability پیشنهاد می‌کند؛ `alg=EdDSA`، `kid` و bindingهای DataSense در protected header قرار می‌گیرند. RFC 8037 الگوریتم `EdDSA` را برای Ed25519 در JOSE تعریف می‌کند. [2]

```json
{
  "payload": "base64url(canonical receipt payload)",
  "protected": "base64url({\"alg\":\"EdDSA\",\"kid\":\"org-acme-sign-2026-09\",\"typ\":\"datasense-receipt+jws\",\"crit\":[\"dsctx\"],\"dsctx\":\"datasense:receipt:v1\"})",
  "signature": "base64url(ed25519 signature over ASCII(protected + '.' + payload))"
}
```

`dsctx` یک domain-separation marker در protected header است؛ verifier فقط contextهای allow-listed را می‌پذیرد. استفاده از `Ed25519ctx` low-level به library API وابسته است؛ نباید curve arithmetic یا context mechanics را دستی پیاده‌سازی کرد. برای کتابخانه‌های استاندارد Ed25519، JWS protected header + typed payload + `typ`/`dsctx` domain separation عملی و قابل‌interoperability است.

### ۳.۲ payloadی که امضا می‌شود

```json
{
  "schema": "datasense.decision-receipt/v2",
  "receipt_id": "opaque-uuid",
  "issuer": "urn:datasense:issuer:acme",
  "issuer_tenant": "opaque-tenant-id",
  "receiver_relationship_id": "opaque-relationship-id",
  "issued_at": "2026-09-01T00:00:00Z",
  "expires_at": "2026-09-01T00:15:00Z",
  "action": {"type": "report.html", "risk": "internal", "purpose_code": "audited_review"},
  "outcome": "allow",
  "evidence_binding": {"bundle_sha256": "sha256:...", "lineage_sha256": "sha256:..."},
  "policy_digest": "sha256:...",
  "privacy": {"contains_raw_dataset_values": false, "contains_local_source_paths": false},
  "nonce": "opaque-random-id"
}
```

Payload نباید recipient PII، row داده، local path، prompt، bearer token، execution key یا provider credential داشته باشد. `execution_key` توسط **receiver Action Gate** پس از verify تولید می‌شود؛ issuer نمی‌تواند capability token قابل‌استفاده در سیستم receiver صادر کند.

### ۳.۳ verifier sequence

```text
JWS JSON input
  → strict JSON parser: duplicate key / size / depth / schema reject
  → protected header: alg=EdDSA, typ, dsctx, kid, issuer consistency
  → relationship lookup: issuer + receiver + environment + action taxonomy
  → pinned/JWKS key lookup: (issuer, kid), kty=OKP, crv=Ed25519, use=sig
  → Ed25519 verify over exact JWS signing input
  → canonical payload digest and inner Evidence Bundle verification
  → issuer/tenant/policy/evidence/lineage binding
  → expiry / clock / action / purpose / privacy / revocation / nonce checks
  → local Action Gate creates one-time execution key only if allow
```

JWS and JWK parsers باید duplicate JSON memberها را reject کنند. RFC 7517 نیز صراحتاً parser handling duplicate members را مهم می‌داند و private key material را خارج از public JWK Set نگه می‌دارد. [3]

## ۴. برنامهٔ مهاجرت مرحله‌ای از HMAC به Ed25519

| فاز | scope | رفتار signer | رفتار verifier | gate خروج |
|---|---|---|---|---|
| M0 — Inventory | local/staging | HMAC فقط | HMAC فقط | map تمام producer/verifier/key ID و test vectorها |
| M1 — Crypto abstraction | code/test | HMAC | HMAC + Ed25519 verifier disabled-by-policy | `Signer`/`Verifier` interface، malformed/key-mismatch tests |
| M2 — Dual-sign shadow | synthetic pilot | HMAC + Ed25519 | هر دو verify؛ HMAC verdict authoritative | Ed/HMAC payload digest و claims binding برابر |
| M3 — Receiver interoperability | two synthetic orgs | dual-sign | Ed25519 verify برای trust relationship محدود | independent receiver، pinned JWKS و rotation drill pass |
| M4 — Ed25519 preferred | limited internal/exchange action | dual-sign | Ed25519 authoritative؛ HMAC fallback فقط receiptهای legacy | no downgrade، revocation و clock skew drills pass |
| M5 — HMAC retirement | exchange only | Ed25519 | Ed25519 only برای action جدید | retention window پایان یافته و customer migration complete |

Rollback migration باید در هر فاز ممکن باشد: verifier Ed25519 defect به `HMAC-only` برای local receipts برمی‌گردد، اما exchange action جدید به allow خودکار تبدیل نمی‌شود. اگر key discovery یا issuer trust unavailable شد، verdict external باید `block` یا `approval_required` باشد.

### ۴.۱ interface پیشنهادی

```python
class ReceiptSigner(Protocol):
    algorithm: str
    async def sign(self, *, payload_bytes: bytes, signing_context: str) -> SignatureEnvelope: ...

class ReceiptVerifier(Protocol):
    algorithm: str
    async def verify(
        self,
        *,
        envelope: SignatureEnvelope,
        payload_bytes: bytes,
        relationship: TrustRelationship,
        now: datetime,
    ) -> VerificationResult: ...
```

کلید خصوصی باید در KMS/HSM یا service جداگانه قرار گیرد؛ application process فقط `sign` را صدا می‌زند و private bytes را log/export نمی‌کند. برای local development، key fixture فقط test-only است و production configuration آن را reject می‌کند.

```python
# pseudocode: library-provided Ed25519; no custom curve math
protected = canonical_jws_header({"alg": "EdDSA", "kid": key.kid, "typ": "datasense-receipt+jws", "dsctx": "datasense:receipt:v1"})
payload = canonical_json(receipt_payload)
signing_input = b64url(protected) + b"." + b64url(payload)
signature = await kms.ed25519_sign(key_id=key.kid, message=signing_input)

public_key = await trusted_jwks.resolve(issuer, kid, relationship)
public_key.verify(signature, signing_input)  # raises → invalid signature
```

## ۵. Rotation، revocation و downgrade protection

| کنترل | الزام |
|---|---|
| Key rotation | issuer ابتدا key جدید را publish می‌کند، سپس dual-sign می‌کند، بعد receiver verification telemetry را بررسی می‌کند و در پایان key قدیمی را retire می‌کند. |
| Key validity | `not_before` و `not_after` در registry؛ receipt `issued_at` در بازهٔ کلید باشد. |
| Revocation | key status signed/pinned یا registry-controlled؛ key revoked برای action جدید invalid است. تاریخچهٔ graph حذف نمی‌شود و به `revoked_key` تغییر status می‌دهد. |
| JWKS cache | TTL bounded، stale-if-error فقط طبق policy و هرگز برای key revoked؛ fresh unknown key به allow منتهی نمی‌شود. |
| Algorithm pinning | relationship فقط `EdDSA` + `OKP` + `Ed25519` را برای v2 exchange می‌پذیرد؛ `alg=none`، HMAC یا curve/key-type mismatch رد می‌شود. |
| Downgrade protection | receipt v2 exchange که Ed25519 لازم دارد با HMAC fallback پذیرفته نمی‌شود؛ HMAC فقط برای schema/issuer scope legacy مشخص مجاز است. |
| Incident response | key compromise → issuance stop، registry revocation، Action Gate containment، receiver notification و forensic graph checkpoint. |

## ۶. CAS Coordinator: هدف و invariantها

Automatic rollback هم‌زمان ممکن است از metric burn-rate، graph checkpoint mismatch، signed alert یا operator API trigger شود. CAS coordinator باید تضمین کند که صد trigger به scope یکسان، حداکثر یک containment state موثر بسازند و هیچ actionی با permit قدیمی بعد از rollback اثر خارجی نگذارد.

### ۶.۱ invariantهای غیرقابل‌مذاکره

1. در هر `(tenant_id, scope)` فقط یک state version معتبر وجود دارد.
2. یک `trigger_evidence_digest` فقط یک rollback event idempotent می‌سازد.
3. rollback فقط state را به سمت ایمن‌تر می‌برد: `execution_mode → suppress_external` و circuit فقط `OPEN` می‌شود.
4. `last_known_good_policy_digest` immutable و پیشاپیش approved است؛ rollback هرگز candidate جدید انتخاب نمی‌کند.
5. Action permit باید **fencing token** (`gate_epoch`) داشته باشد؛ commit action تنها زمانی مجاز است که epoch receipt با state epoch جاری برابر باشد.
6. audit outbox و state transition در همان تراکنش persist می‌شوند.
7. `UNKNOWN`، DB error یا CAS exhaustion به allow تبدیل نمی‌شود.

### ۶.۲ tableهای تکمیلی

```sql
ALTER TABLE action_gate_rollout_states
  ADD COLUMN gate_epoch BIGINT NOT NULL DEFAULT 0;

CREATE TABLE action_gate_permits (
  tenant_id UUID NOT NULL,
  scope TEXT NOT NULL,
  execution_key TEXT NOT NULL,
  gate_epoch BIGINT NOT NULL,
  receipt_digest TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('reserved','committed','suppressed','expired')),
  expires_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (tenant_id, execution_key)
);

CREATE UNIQUE INDEX action_gate_rollback_dedupe
  ON action_gate_rollback_events (tenant_id, scope, trigger_evidence_digest);
```

`gate_epoch` با هر transition که verdict external را محدود یا آزاد می‌کند افزایش می‌یابد. Action Gate هر permit را با epoch جاری reserve می‌کند. downstream commit با `WHERE state='reserved' AND gate_epoch=:decision_epoch AND expires_at > now()` و مقایسه با rollout state اجرا می‌شود.

### ۶.۳ SQL transaction برای rollback

```sql
BEGIN;

-- مرحلهٔ ۱: trigger dedupe؛ اگر conflict، فقط نتیجهٔ event موجود بازگردد.
INSERT INTO action_gate_rollback_events (
  rollback_id, tenant_id, scope, trigger_type, trigger_evidence_digest,
  previous_state, target_state, transition_status, created_at
)
VALUES (
  :rollback_id, :tenant_id, :scope, :trigger_type, :trigger_digest,
  '{}'::jsonb, '{}'::jsonb, 'pending', now()
)
ON CONFLICT (tenant_id, scope, trigger_evidence_digest) DO NOTHING
RETURNING rollback_id;

-- اگر row بازنگردد: COMMIT؛ rollback قبلاً توسط request دیگر پذیرفته شده است.

-- مرحلهٔ ۲: conditional state transition؛ row lock با UPDATE/CAS، نه distributed lock.
WITH current AS (
  SELECT tenant_id, scope, version, gate_epoch, mode, execution_mode,
         active_policy_digest, last_known_good_policy_digest
  FROM action_gate_rollout_states
  WHERE tenant_id = :tenant_id AND scope = :scope
  FOR UPDATE
), changed AS (
  UPDATE action_gate_rollout_states s
  SET mode = 'rollback_active',
      execution_mode = 'suppress_external',
      active_policy_digest = c.last_known_good_policy_digest,
      version = c.version + 1,
      gate_epoch = c.gate_epoch + 1,
      updated_at = now()
  FROM current c
  WHERE s.tenant_id = c.tenant_id
    AND s.scope = c.scope
    AND s.version = :expected_version
    AND s.mode IN ('limited_enforce', 'enforce', 'shadow')
  RETURNING s.*
)
SELECT * FROM changed;

-- مرحلهٔ ۳: state snapshot، outbox audit و rollback event completion در همان تراکنش.
INSERT INTO outbox (... action_gate_rollback_activated ...);
UPDATE action_gate_rollback_events
SET previous_state = :previous_redacted_json,
    target_state = :target_redacted_json,
    transition_status = 'committed', completed_at = now()
WHERE rollback_id = :rollback_id;

COMMIT;
```

در implementation، کاربرد `FOR UPDATE` و `version` هر دو عمدی است: row lock state snapshot را serial می‌کند و version check از writer stale یا retry با expectation قدیمی جلوگیری می‌کند. isolation `READ COMMITTED` با row lock و unique constraint برای این transition کافی است؛ اگر queryهای rollback به predicateهای چندscope تکیه کنند، باید transaction scope و isolation جداگانه طراحی شود، نه اینکه بی‌دلیل global serializable فعال شود.

### ۶.۴ pseudocode Coordinator

```python
async def handle_rollback_trigger(trigger: RollbackTrigger) -> RollbackOutcome:
    trigger.validate_bounded_shape()
    await trigger_verifier.verify(trigger)  # signed alert / metric attestation / graph proof

    for attempt in range(3):
        async with repository.transaction() as tx:
            rollback_id = await tx.insert_rollback_intent_once(
                tenant_id=trigger.tenant_id,
                scope=trigger.scope,
                trigger_digest=trigger.evidence_digest,
                trigger_type=trigger.type,
            )
            if rollback_id is None:
                existing = await tx.get_rollback_by_trigger(trigger)
                return RollbackOutcome("already_handled", existing.rollback_id)

            state = await tx.get_rollout_state_for_update(trigger.tenant_id, trigger.scope)
            if state is None:
                await tx.mark_rollback_suppressed(rollback_id, "rollout_state_unknown")
                return RollbackOutcome("suppressed_state_unknown", rollback_id)

            if state.execution_mode == "suppress_external" or state.mode == "manual_kill":
                await tx.mark_rollback_completed(rollback_id, state.redacted())
                return RollbackOutcome("already_contained", rollback_id)

            result = await tx.cas_activate_rollback(
                tenant_id=state.tenant_id,
                scope=state.scope,
                expected_version=state.version,
                expected_epoch=state.gate_epoch,
                rollback_id=rollback_id,
                target_policy_digest=state.last_known_good_policy_digest,
            )
            if result is None:
                await tx.remove_uncommitted_rollback_intent(rollback_id)
                continue

            await tx.append_audit_outbox(
                event_type="action_gate_rollback_activated",
                metadata=result.redacted_event_metadata(trigger),
            )
            await tx.mark_rollback_committed(rollback_id, result)

        # DB state is authoritative and already blocks new permits.
        # This side effect is retried via durable outbox; it cannot reopen permissions.
        await rollback_outbox.enqueue_circuit_open(scope=trigger.scope, reason=trigger.reason_code)
        return RollbackOutcome("rollback_active", rollback_id)

    return RollbackOutcome("suppressed_cas_contention")
```

در contention exhaustion، Coordinator باید `suppress_cas_contention` ثبت کند و Action Gate با state read failure `suppress_external` کند. نباید از retries نامحدود، in-memory lock به‌عنوان source of truth یا lock Redis بدون fencing استفاده شود.

### ۶.۵ جلوگیری از TOCTOU با fencing permit

CAS فقط rollout state را امن نمی‌کند؛ permitی که پیش از rollback صادر شده نیز خطر دارد. بنابراین commit action باید fence شود:

```python
async def commit_effect(permit: Permit, effect: ExternalEffect) -> None:
    async with repository.transaction() as tx:
        state = await tx.get_rollout_state_for_update(permit.tenant_id, permit.scope)
        if state.execution_mode != "allow_guarded":
            raise Suppress("suppressed_rollback_active")
        if state.gate_epoch != permit.gate_epoch:
            raise Suppress("suppressed_stale_gate_epoch")
        reserved = await tx.consume_permit_once(
            execution_key=permit.execution_key,
            expected_epoch=permit.gate_epoch,
        )
        if not reserved:
            raise Suppress("suppressed_replayed_or_expired_permit")
        await tx.record_execution_started(permit.execution_key)

    # provider call after reservation; provider idempotency key = execution_key
    provider_result = await provider.call(idempotency_key=permit.execution_key, effect=effect)
    await repository.record_effect_or_unknown(permit.execution_key, provider_result)
```

اگر rollback بین preflight و commit اتفاق بیفتد، `gate_epoch` افزایش یافته و commit رد می‌شود. اگر rollback بعد از provider call اتفاق بیفتد، execution ledger به وضعیت effect/unknown مراجعه می‌کند و rollback اثر قبلی را حدس نمی‌زند.

### ۶.۶ race matrix

| race | کنترل | نتیجهٔ مورد انتظار |
|---|---|---|
| دو trigger با digest یکسان | unique `(tenant, scope, trigger_digest)` | فقط یک event/transition؛ بقیه `already_handled` |
| دو trigger متفاوت در یک scope | row lock + version + safe-state check | نخستین containment فعال؛ دومی `already_contained` |
| operator manual kill هم‌زمان | state precedence `manual_kill > rollback_active` | manual kill باقی می‌ماند؛ rollback close نمی‌کند |
| preflight allow سپس rollback | `gate_epoch` fencing | commit action stale suppress می‌شود |
| commit permit سپس rollback | execution reservation + provider idempotency | effect نهایتاً یک‌بار یا unknown؛ duplicate ممنوع |
| DB commit موفق، response timeout | idempotency event و query by trigger | retry outcome موجود را برمی‌گرداند |
| DB update موفق، circuit outbox delayed | DB `suppress_external` authoritative | new permit allow نمی‌شود؛ circuit open eventually delivered |
| graph mismatch و policy author هم‌زمان | rollback target = immutable last-known-good | candidate policy هیچ‌گاه rollback target نیست |

## ۷. آزمون‌های پذیرش Ed25519 و CAS

| گروه | سناریو | PASS condition |
|---|---|---|
| Ed25519 vector | RFC 8032/8037 positive و negative vector | signature معتبر accept، هر byte change reject [1] [2] |
| JWK safety | duplicate member، wrong `kty/crv/alg`، unknown `kid` | strict reject؛ no fallback |
| Dual sign | یک payload HMAC + Ed25519 | claim/binding یکسان؛ Ed verifier مستقل pass |
| Key rotation | key N و N+1 overlap، N revoke | N+1 valid؛ N receipt جدید reject پس از revoke |
| Trust relationship | issuer صحیح اما action خارج scope | `approval_required` یا block؛ signature alone کافی نیست |
| CAS dedupe | 100 concurrent trigger مشابه synthetic | یک rollback event committed |
| CAS contention | triggerهای متفاوت یک scope | execution mode نهایی suppress_external؛ هیچ allow بعدی نیست |
| Fencing | permit epoch N، rollback به N+1 | commit N reject؛ provider call = 0 |
| Crash recovery | crash بعد از state commit قبل circuit open | DB gate block؛ outbox eventually opens circuit |
| Graph proof | checkpoint/reconciliation tamper | mismatch alert → R1/R2 containment |

## ۸. اسکریپت ارائهٔ فنی و سرمایه‌گذاری

این اسکریپت برای ۱۰ اسلاید deck «Proof-Carrying Decisions» نوشته شده است و بسته به مخاطب ۱۲ تا ۱۵ دقیقه زمان می‌گیرد.

### اسلاید ۱ — Thesis

«ایدهٔ مرکزی ساده است: یک action داده‌محور نباید فقط بر اساس یک permission خام یا dashboard سبز اجرا شود. باید پیش از اثر خارجی، proof قابل‌راستی‌آزمایی داشته باشد. ما این دسته را Proof-Carrying Decisions می‌نامیم. این ادعای برتری بازار نیست؛ فرضیه‌ای است که می‌خواهیم با design partner و evidence بسنجیم.»

### اسلاید ۲ — Gap بازار

«ابزارهای موجود به ما می‌گویند چه چیزی خراب شده، data از کجا آمده یا یک agent چه permissionی دارد. gap بین این‌ها، لحظهٔ action است. DataSense تلاش می‌کند تصمیم را به evidence و policy متصل کند تا بعداً بتوان پرسید: چرا این export یا agent action مجاز شد؟»

### اسلاید ۳ — Decision Fabric

«چهار لایه داریم: trust evidence، policy deterministic، receipt امضاشده و Action Gate. تفاوت مهم این است که unknown هیچ‌گاه allow نیست. Approval نیز quality block یا evidence tamper را override نمی‌کند. این architecture همزمان foundation محصول و safety boundary ماست.»

### اسلاید ۴ — Receipt منتشرشده

«نقطهٔ شروع عملی ما Trust Decision Receipt است. core فعلی canonical digest، HMAC signature، expiry، action scope و privacy metadata-only دارد. این receipt هنوز executor نیست؛ عمداً execution از proof جدا مانده تا Action Gate بتواند آن را کنترل کند.»

### اسلاید ۵ — Policy Grammar

«برای جلوگیری از policy مبهم، DSL محدود داریم. policy versioned، canonical و قابل simulation است. تغییر policy که block را allow می‌کند، relaxation محسوب می‌شود و نیازمند approval، blast-radius evidence و rollback plan است.»

### اسلاید ۶ — Policy Simulator و Evidence Graph

«Simulator پیش از enforcement، candidate را روی snapshotهای immutable replay می‌کند. Evidence Graph پاسخ می‌دهد proof از کجا آمده و به چه actionی منتهی شده. Graph منبع permission نیست؛ بلکه یک chain-of-custody queryable است که node و edgeهایش content-addressed و checkpointed هستند.»

### اسلاید ۷ — Action Gate و Automatic Rollback

«Gate با stage-gate-commit کار می‌کند. در rollback، ما اثرهای جدید را متوقف می‌کنیم، circuit را باز می‌کنیم و به policy approved قبلی بازمی‌گردیم؛ اما receipt و audit را حذف نمی‌کنیم. بازگشت از rollback خودکار نیست: shadow، approval و half-open محدود لازم است.»

### اسلاید ۸ — Ed25519 و Trust Exchange

«برای exchange بین‌سازمانی، HMAC کافی نیست، چون verifier نباید secret issuer را دریافت کند. در Ed25519، issuer با private key امضا می‌کند و receiver با public key pinned/JWKS verify می‌کند. اما cryptography به‌تنهایی trust نیست؛ issuer onboarding، relationship scope، key rotation و revocation بخشی از محصول هستند.»

### اسلاید ۹ — CAS و سرمایه‌گذاری روی safety

«race condition یک مشکل تئوریک نیست: ممکن است action permit گرفته باشد و هم‌زمان rollback فعال شود. CAS coordinator state version و gate epoch را atomically افزایش می‌دهد. permit قدیمی fencing می‌شود و commit effect رد می‌شود. این سرمایه‌گذاری، هزینهٔ incident و bypass را پیش از scale کاهش می‌دهد.»

### اسلاید ۱۰ — درخواست تصمیم

«درخواست امروز rollout انبوه نیست. یک design partner با workflow کم‌خطر، synthetic scope، ownerهای Security/SRE/Policy و budget stage-gated می‌خواهیم. معیار Go این است که receiver مستقل proof را verify کند و workflow بدون bypass استفاده شود. اگر این رخ ندهد، Narrow، Pivot یا Stop تصمیم‌های معتبرند.»

## References

[1] [RFC 8032 — Edwards-Curve Digital Signature Algorithm (EdDSA)](https://www.rfc-editor.org/rfc/rfc8032.html)

[2] [RFC 8037 — Ed25519/Ed448 in JOSE](https://www.rfc-editor.org/rfc/rfc8037.html)

[3] [RFC 7517 — JSON Web Key (JWK)](https://www.rfc-editor.org/rfc/rfc7517.html)
