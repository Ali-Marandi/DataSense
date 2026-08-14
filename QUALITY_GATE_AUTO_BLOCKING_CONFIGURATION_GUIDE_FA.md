# پیکربندی پیشرفتهٔ Quality Gates و Auto-Blocking در Trust Center

## وضعیت فعلی محصول

Trust Center اکنون Data Contract، `QualityGatePolicy`، score وزن‌دار، quality history، export evidence و نمایش decision را اجرا می‌کند. `DataManager.run_governance_checks()` report را ایجاد می‌کند و `report.gate_decision(manager.quality_gate_policy)` را در history ثبت می‌نماید. UI نتیجه را در کارت **Release Gate** نمایش و export JSON را شامل policy، decision و reasons می‌کند.

> **مرز مهم:** در desktop فعلی، `blocked` یک تصمیم evidence-based است؛ این تصمیم dataset را حذف یا تغییر نمی‌دهد و به‌تنهایی دکمه‌های export در سایر workspaceها را قفل نمی‌کند. Auto-blocking عملی زمانی رخ می‌دهد که action حساس—مانند export، publish، scheduled pipeline یا handoff—صریحاً پیش از اجرا Gate را enforce کند.

ویرایشگر گرافیکی Quality Gate در Trust Center فعلی وجود ندارد؛ اما policy از طریق API `DataManager.set_quality_gate_policy()` قابل‌تنظیم است و با پروژهٔ `.dsproj` پایدار می‌ماند. Contract editor موجود، ruleهای data quality را به‌صورت UI پیکربندی می‌کند.

## اجزای تصمیم Gate

| جزء | نقش | تغییر داده؟ |
|---|---|---|
| `DataContract` | مجموعه ruleهای قابل‌اجرا برای dataset | خیر |
| `QualityReport` | evidence یک اجرا: result، violation، score، status | خیر |
| `QualityGatePolicy` | حداقل score، سقف failure critical/high، block-on-error | خیر |
| `QualityGateDecision` | `approved`، `blocked` یا `not configured` همراه reason | خیر |
| enforcement hook | توقف action حساس اگر Gate مجاز نباشد | باید فقط action را متوقف کند، نه داده را mutate نماید. |

فرمول score چنین است:

```text
score = round(100 × Σ(weight ruleهای pass) / Σ(weight ruleهای evaluated), 1)
```

وزن‌ها critical=4، high=3، medium=2 و low=1 هستند. score و Gate عمداً مستقل‌اند. یک score نسبتاً بالا ممکن است به‌علت failure high/critical یا rule error همچنان Gate را blocked کند.

## profileهای پیشنهادی

| profile | `minimum_score` | `maximum_critical_failures` | `maximum_high_failures` | `block_on_error` | کاربرد مناسب |
|---|---:|---:|---:|---|---|
| Sandbox review | 80 | 0 | 3 | false | تحلیل اکتشافی؛ export حساس همچنان نیازمند review. |
| Internal analytics | 95 | 0 | 1 | true | dashboard داخلی و گزارش غیرحساس. |
| Tier-1 release | 98 | 0 | 0 | true | گزارش مالی، executive KPI، خروجی customer-facing. |
| Restricted/regulated | 100 یا rule اختصاصی | 0 | 0 | true | PII/restricted export با approval اضافه. |

اعداد profileها پیشنهاد شروع هستند، نه قانون جهانی. مالک داده باید احتمال/اثر خطا، remediation SLA، consumer criticality و هزینهٔ false-positive را بررسی کند. تعداد زیاد rule critical باعث bypass غیررسمی می‌شود؛ severity critical فقط برای نقض‌هایی استفاده شود که واقعاً مصرف را ناامن یا غیرقابل‌دفاع می‌کنند.

## تنظیم policy با API فعلی

```python
from core.governance import QualityGatePolicy
from core.data_manager import DataManager

manager = DataManager()
# manager.load(...) یا assignment data پیش از این مرحله انجام شده است.

policy = QualityGatePolicy(
    name="Tier-1 monthly release gate",
    minimum_score=98.0,
    maximum_critical_failures=0,
    maximum_high_failures=0,
    block_on_error=True,
)
manager.set_quality_gate_policy(policy)

report = manager.run_governance_checks()
decision = report.gate_decision(manager.quality_gate_policy)
print(decision.to_dict())
```

`QualityGatePolicy` در زمان ساخت اعتبارسنجی می‌شود: score باید در بازهٔ ۰ تا ۱۰۰ باشد و failure limitها منفی نباشند. contract باید پیش از اجرا با `manager.set_governance_contract(contract)` ثبت شود. mutation dataset یا تغییر contract، `governance_report` را invalid می‌کند؛ action حساس نباید از report قدیمی استفاده کند.

## مثال Contract سخت‌گیرانه

```python
from core.governance import DataContract, DataQualityRule

contract = DataContract(
    name="Financial month-close contract",
    rules=[
        DataQualityRule("not_null", "ledger_entry_id", severity="critical"),
        DataQualityRule("unique", "ledger_entry_id", severity="critical"),
        DataQualityRule("range", "amount", {"min": -10_000_000, "max": 10_000_000}, severity="high"),
        DataQualityRule("allowed_values", "currency", {"values": ["USD", "EUR", "IRR"]}, severity="high"),
        DataQualityRule("freshness", "loaded_at", {"max_age_days": 1}, severity="high"),
    ],
)
manager.set_governance_contract(contract)
```

برای range مالی، حدهای واقعی باید از domain owner و currency/unit semantics بیایند. برای freshness، timezone و معنای `loaded_at` باید روشن باشد. recommended rules در UI نقطهٔ شروع هستند؛ آن‌ها policy نهایی بدون review نیستند.

## Auto-blocking در action حساس

تابع زیر الگوی enforcement برای export/publish است. قبل از استفاده، باید report جدید وجود داشته باشد؛ بهتر است `run_governance_checks()` درست در ابتدای workflow حساس اجرا شود.

```python
class QualityGateBlocked(RuntimeError):
    pass


def require_quality_approval(manager: DataManager, action: str) -> None:
    report = manager.governance_report
    if report is None:
        raise QualityGateBlocked(f"{action} blocked: quality checks have not been run.")

    decision = report.gate_decision(manager.quality_gate_policy)
    if not decision.allowed:
        reasons = "; ".join(decision.reasons)
        raise QualityGateBlocked(f"{action} blocked by '{decision.policy_name}': {reasons}")


def export_parquet(manager: DataManager, destination: str) -> None:
    require_quality_approval(manager, "Parquet export")
    manager.df.to_parquet(destination, index=False)
```

در application UI، exception باید به پیام قابل‌فهم تبدیل شود و **reasonهای Gate، لینک evidence export و مسیر remediation** را نشان دهد. Auto-blocking نباید dataframe را حذف کند، rule را silent تغییر دهد یا evidence failure را پاک کند.

## ترکیب Quality Gate با Schema Drift

یک Quality Gate approved تضمین نمی‌کند schema با baseline سازگار است. برای handoff حساس، هر دو Gate و Schema Drift Guard باید approval داشته باشند.

```python
class ReleaseBlocked(RuntimeError):
    pass


def require_release_approval(manager: DataManager, action: str) -> None:
    require_quality_approval(manager, action)
    drift = manager.check_schema_drift()
    if drift.decision != "compatible":
        raise ReleaseBlocked(
            f"{action} blocked by schema policy '{drift.policy_name}': "
            + "; ".join(drift.reasons)
        )
```

Lineage Tracker مکمل این تصمیم است: پیش از override یا approval، latest transformationها و row-count impact را بررسی کنید. Lineage به‌تنهایی مجوز release نیست.

## پیکربندی در UI فعلی: workflow گام‌به‌گام

ابتدا dataset را import کنید. در Trust Center روی **Scan sensitive data** کلیک کنید و signalهای Restricted/Confidential را بازبینی نمایید. سپس نام contract را وارد کنید، ruleهای مناسب را از form اضافه کنید یا **Add recommended rules** را به‌عنوان starter انتخاب نمایید. severity و JSON parameters هر rule را پیش از reliance بررسی کنید.

بعد از تعیین policy از طریق API/project config، روی **Run quality checks** کلیک کنید. کارت Release Gate و جدول result را بخوانید. اگر `blocked` است، action حساس را متوقف نگه دارید، evidence JSON را صادر و failure را triage کنید. بعد از رفع data defect یا اصلاح reviewشدهٔ rule، دوباره check را اجرا کنید. برای schema، baseline فقط پس از approval ثبت و سپس `Check schema drift` اجرا شود.

## Blocking rules و precedence

ترتیب تصمیم در implementation فعلی چنین است:

| شرط | نتیجه Gate | دلیل |
|---|---|---|
| هیچ rule ارزیابی نشده | `not configured` | score معتبر موجود نیست. |
| `block_on_error=True` و حداقل یک rule error | `blocked` | پیکربندی/اجرای rule نیاز به review دارد. |
| critical failures بیش از limit | `blocked` | حد critical نقض شده است. |
| high failures بیش از limit | `blocked` | حد high نقض شده است. |
| score کمتر از minimum | `blocked` | کیفیت وزن‌دار زیر policy است. |
| همهٔ موارد بالا عبور کند | `approved` | شرط‌های Gate برقرارند. |

Gate همهٔ reasonهای قابل‌اعمال را جمع می‌کند؛ بنابراین remediation نباید فقط اولین reason را رفع کند. مثلاً repair یک high failure ممکن است score را همچنان زیر minimum نگه دارد.

## Override کنترل‌شده

override باید یک workflow سازمانی باشد، نه دکمهٔ bypass دائمی. در Control Plane آینده، تنها permission `contract.override_block` برای roleهای محدود مانند Owner/Admin/Data Steward مناسب است. override record باید شامل actor، organization، action، contract/policy version، reasons، ticket/correlation ID، scope، timestamp و TTL باشد.

```python
@dataclass(frozen=True)
class GateOverride:
    action: str
    ticket_id: str
    reason: str
    expires_at: str
    approved_by: str


def require_override_or_approval(manager, action: str, override: GateOverride | None) -> None:
    try:
        require_release_approval(manager, action)
    except (QualityGateBlocked, ReleaseBlocked):
        if override is None:
            raise
        # Production: validate actor permission, TTL, ticket and audit atomically server-side.
        if not override.ticket_id or not override.reason:
            raise QualityGateBlocked("Override is missing a ticket or reason.")
```

در desktop standalone، override نباید صرفاً با local boolean انجام شود. برای implementation سازمانی، validation و audit باید server-side باشد. هر override بعد از TTL منقضی می‌شود و برای run جدید باید دوباره review شود.

## تست‌های ضروری auto-blocking

| test | setup | expected assertion |
|---|---|---|
| G-01 | report غایب | export action با پیام `checks have not been run` block شود. |
| G-02 | failure critical | `require_quality_approval` exception بدهد. |
| G-03 | high failure، score ظاهراً بالا | limit high=0 action را block کند. |
| G-04 | execution error | block-on-error=true action را block کند. |
| G-05 | Gate approved + drift blocked | `require_release_approval` action را block کند. |
| G-06 | data mutation بعد از run | report invalid شود و run مجدد لازم باشد. |
| G-07 | override expired/unauthorized | action block و audit deny. |
| G-08 | export evidence | policy، decision، reasons، history، drift و lineage metadata وجود داشته باشد. |

## Runbook برای `blocked`

ابتدا action حساس را hold کنید. report، Gate decision و Schema Drift report را export نمایید. failure را به data defect، schema change، rule parameter یا execution error دسته‌بندی کنید. root cause upstream را اصلاح یا policy/contract change را با owner review ثبت کنید. سپس check را دوباره اجرا کنید. فقط decision approved و schema compatible، یا override دارای TTL و audit، اجازهٔ ادامه می‌دهد.

این فرایند باید به‌جای حذف silent rule یا تغییر baseline برای عبور سریع، evidence و change history را حفظ کند.
