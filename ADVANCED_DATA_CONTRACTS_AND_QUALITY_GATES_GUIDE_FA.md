# راهنمای پیشرفتهٔ Data Contracts و Quality Gates در Trust Center

## مدل عملیاتی

Data Contract در DataSense مجموعه‌ای versionable از `DataQualityRule`هاست که بر یک DataFrame اعمال می‌شود. هر rule دارای `rule_type`، `column`، `params`، `severity` و `name` است. اجرای contract یک `QualityReport` immutable-at-export ایجاد می‌کند. **Quality Score** نتیجهٔ وزن‌دار ruleهای اجراشده است؛ **Quality Gate** policy مستقلی است که score، failureهای critical/high و errorهای اجرا را به تصمیم `approved` یا `blocked` تبدیل می‌کند.

> Contract انتظار قابل‌آزمون را مشخص می‌کند؛ Report evidence اجراست؛ Gate تصمیم مجازبودن یک مصرف یا release است. این سه را در مستندات یا workflow سازمانی با هم اشتباه نگیرید.

## طراحی Contract: از asset تا rule

ابتدا asset، owner، consumer، criticality و هدف مصرف را مشخص کنید. سپس برای هر ستون مهم، rule را بر پایهٔ risk، نه صرفاً قابلیت فنی، انتخاب کنید. ستون‌های کلید، join، feature مدل، metric مالی، PII و timestamp freshness معمولاً حساس‌ترین نقطه‌ها هستند.

| نوع asset | ruleهای پایه | ruleهای سخت‌گیر | هدف Gate |
|---|---|---|---|
| گزارش مدیریتی فروش | `not_null`, `unique`, `range`, `allowed_values` | freshness، regex شناسه، drift policy | جلوگیری از تصمیم بر دادهٔ ناقص یا تکراری. |
| dataset مالی Tier-1 | کلید critical، range high، freshness high | critical limits صفر، `block_on_error=True` | block export/reporting در هر failure مهم. |
| feature set مدل | not-null feature، range، allowed category | schema drift strict، lineage review | جلوگیری از تغییر silent feature/type. |
| exploration sandbox | recommended rules reviewable | Gate permissive و export محدود | مشاهدهٔ issue بدون متوقف‌کردن discovery. |

## ruleهای پشتیبانی‌شده و پیکربندی

| `rule_type` | `params` نمونه | کاربرد | خطر رایج |
|---|---|---|---|
| `not_null` | `{}` | کلیدها، timestampها و fieldهای اجباری | اعمال روی fieldهای ذاتاً optional. |
| `unique` | `{}` | identifierهای یکتا | استفاده برای ستون‌هایی که granularity آن‌ها اشتباه فهمیده شده است. |
| `range` | `{"min": 0, "max": 1000000}` | مبلغ، count، درصد، date numeric | حدهای static که با business seasonality سازگار نیستند. |
| `allowed_values` | `{"values": ["North", "South"]}` | enumها و stateها | فراموش‌کردن migration ارزش جدید. |
| `regex` | `{"pattern": "^[A-Z]{2}-[0-9]{4}$"}` | code/identifier format | regex بسیار strict برای دادهٔ legacy. |
| `freshness` | `{"max_age_days": 1}` | datasetهای batch دارای timestamp | عدم تعریف time-zone/semantics timestamp. |

در UI، Data Contract name را متناسب با domain و هدف قرار دهید؛ برای نمونه `Monthly sales release contract`. یک rule با severity `critical` باید نشان دهد failure آن واقعاً مصرف داده را متوقف می‌کند. overuse severity critical باعث alert fatigue و bypass غیررسمی خواهد شد.

## نمونه‌کد: ساخت Contract به‌صورت برنامه‌نویسی

```python
import pandas as pd
from core.governance import DataContract, DataQualityRule, QualityGatePolicy

contract = DataContract(
    name="Monthly sales release contract",
    rules=[
        DataQualityRule("not_null", "order_id", severity="critical", name="Order identifier is present"),
        DataQualityRule("unique", "order_id", severity="critical", name="Order identifier is unique"),
        DataQualityRule("range", "revenue", {"min": 0, "max": 1_000_000}, severity="high"),
        DataQualityRule("allowed_values", "region", {"values": ["North", "South", "East", "West"]}, severity="medium"),
        DataQualityRule("freshness", "loaded_at", {"max_age_days": 1}, severity="high"),
    ],
)

frame = pd.DataFrame({
    "order_id": ["SO-1", "SO-2"],
    "revenue": [1200, 950],
    "region": ["North", "South"],
    "loaded_at": pd.to_datetime(["2026-08-13", "2026-08-13"]),
})

report = contract.evaluate(frame)
policy = QualityGatePolicy(
    name="Tier-1 monthly release gate",
    minimum_score=98.0,
    maximum_critical_failures=0,
    maximum_high_failures=0,
    block_on_error=True,
)
decision = report.gate_decision(policy)

print(report.summary())
print(decision.to_dict())
assert decision.allowed
```

`DataContract.evaluate()` ruleها را روی DataFrame اجرا می‌کند و نباید frame را mutate نماید. report شامل `observed`، `expected`، `violations` و `detail` است؛ قبل از export evidence بررسی کنید که rule parameter یا detail حاوی secret یا شناسهٔ حساس نباشد.

## فرمول Quality Score

برای ruleهای evaluated، weightها چنین هستند: critical=4، high=3، medium=2 و low=1. فرمول محصول:

```text
score = round(100 × Σ(weight ruleهای pass) / Σ(weight ruleهای evaluated), 1)
```

ruleهای `error` در denominator هستند ولی در numerator نیستند. اگر هیچ rule ارزیابی نشده باشد، score برابر `None` است؛ سیستم به اشتباه score 100 تولید نمی‌کند. status report به‌ترتیب priority چنین است: no evaluated rules = `not configured`؛ وجود error = `needs attention`؛ failure critical = `blocked`؛ failure دیگر = `needs attention`؛ و در غیر این صورت `trusted`.

مثال: یک rule critical pass (4)، یک rule high fail (3) و یک rule medium pass (2) امتیاز `100 × 6 / 9 = 66.7` می‌دهد. حتی اگر minimum score پایین‌تر تنظیم شود، policy با `maximum_high_failures=0` همچنان Gate را block می‌کند. این رفتار مطلوب است زیرا score و policy مستقل‌اند.

## طراحی Quality Gate بر پایهٔ risk

| profile | minimum score | critical failures | high failures | block on error | کاربرد |
|---|---:|---:|---:|---|---|
| Sandbox review | 80 | 0 | 3 | خیر | exploration با human review. |
| Standard analytics | 95 | 0 | 1 | بله | گزارش داخلی و dashboard معمولی. |
| Tier-1 release | 98 | 0 | 0 | بله | گزارش مالی، customer-facing یا metric board. |
| Regulated/restricted | 100 یا policy اختصاصی | 0 | 0 | بله | export محدود، دو approval و controlهای تکمیلی. |

پروفایل Tier-1 باید فقط زمانی استفاده شود که owner، remediation SLA و مسیر override مشخص باشند. `CONTRACT_OVERRIDE_BLOCK` در RBAC باید نقش محدود داشته باشد و هر override با ticket، reason، expiration و audit event ثبت شود؛ override نباید baseline یا report اصلی را حذف کند.

## پیکربندی در Trust Center: مراحل پیشرفته

ابتدا dataset را import و **Scan sensitive data** را اجرا کنید. signalهای Restricted/Confidential را بررسی کنید و به‌ویژه پیش از export یا اشتراک evidence، ستون‌های حساس را شناسایی نمایید. سپس Contract name را تعیین، ruleها را دستی ایجاد یا با recommended rules آغاز کنید. recommended ruleها صرفاً starter هستند و باید توسط owner بازبینی شوند.

پس از **Run quality checks**، این sequence را اجرا کنید: score/status را بررسی کنید؛ failed/error ruleها را بر پایه severity triage کنید؛ Gate decision و reasons را بخوانید؛ history/trend را با اجرای بعدی مقایسه کنید؛ و در نهایت evidence JSON را صادر نمایید. برای dataset production، policy Gate و Contract را همراه `.dsproj` تحت version control یا storage کنترل‌شده نگه‌داری نمایید.

برای تغییر contract، نام/نسخه و دلیل change را ثبت کنید. حذف یک rule critical برای عبور از Gate باید change management تلقی شود. بهتر است policy و contract را با rollout دو مرحله‌ای مدیریت کنید: ابتدا observe-only و measurement، سپس enforce/block بعد از baseline کافی و موافقت owner.

## Quality History و Trend

`QualityHistory` در `.dsproj` تا ۹۰ run به‌صورت پیش‌فرض نگه‌داری می‌کند. هر record شامل نام contract، زمان UTC، row count، score، status و gate decision است؛ cell value ذخیره نمی‌شود. trend فقط آخرین دو score معتبر را مقایسه می‌کند: تغییر حداقل +1.0 = `improving`، تغییر حداکثر −1.0 = `declining` و غیر آن = `stable`.

Trend جایگزین incident یا root-cause analysis نیست. declining trend باید trigger بازبینی upstream، schema drift، freshness و تغییر pipeline باشد. برای alerting مرکزی آینده، فقط eventهای blocked یا decline پایدار باید Pager داشته باشند؛ هر score fluctuation نباید notification پرهزینه ایجاد کند.

## اتصال با Schema Drift و Lineage

Quality Gate value-level contract را ارزیابی می‌کند. Schema Drift Guard سازگاری ساختاری dataset با baseline را بررسی می‌کند و Lineage Tracker operationهای transform را ثبت می‌نماید. Gate approved به معنی نبود schema drift نیست؛ پیش از release حساس هر سه را بازبینی کنید.

| پرسش | کنترل صحیح |
|---|---|
| آیا values ruleهای کیفیت را رعایت می‌کنند؟ | Contract + Quality Report/Gate |
| آیا schema در مقایسه با approved baseline سازگار است؟ | Schema Drift Guard |
| چه transformationی به وضعیت فعلی منجر شد؟ | Data Lineage Tracker |
| آیا می‌توان dataset را به consumer حساس تحویل داد؟ | ترکیب Gate، Drift، Lineage و approval policy |

## Runbook برای Gate blocked

Gate block باید به‌معنای hold مصرف حساس باشد، نه حذف خودکار داده. نخست report و decision reasons را export کنید. سپس failureها را به دو دسته data defect و rule configuration error تفکیک کنید. defect upstream را در source/pipeline برطرف کنید؛ configuration error را با change review اصلاح کنید. contract را مجدداً اجرا نمایید و فقط پس از decision approved release/export را ادامه دهید.

اگر override ضروری است، فقط نقش مجاز باید آن را انجام دهد. Override باید reason، owner، correlation/ticket، scope، TTL و evidence export داشته باشد. bypass دائمی یا silent برای rule critical ضدالگوی سازمانی است.

## آزمون و معیار پذیرش

| سناریو | نتیجهٔ مورد انتظار |
|---|---|
| Contract خالی | score `None` و Gate `not configured`، نه score کامل. |
| failure critical | report `blocked` و Gate blocked با limit صفر. |
| high failure با score ظاهراً قابل‌قبول | Gate blocked وقتی maximum high=0. |
| execution error | اگر `block_on_error=True` است Gate blocked. |
| mutation پس از run | report قبلی stale/invalid شود و دوباره اجرا لازم باشد. |
| project restore | contract، Gate policy و history با `.dsproj` باقی بمانند. |
| evidence privacy | PII finding/history raw value نگه ندارد. |

مجموعهٔ فعلی repository این رفتارهای governance، Schema Drift و Lineage را به‌علاوهٔ security-flow و smoke UI در suite **۸۰ آزمونی** پوشش می‌دهد. این regression evidence جایگزین owner approval، production integration test و audit مستقل نیست.
