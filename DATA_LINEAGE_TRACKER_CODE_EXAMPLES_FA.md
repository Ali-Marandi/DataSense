# Data Lineage Tracker: جزئیات فنی و نمونه‌کدهای استفاده

## هدف و دامنه

**Data Lineage Tracker** در DataSense یک trail محلی، bounded و privacy-preserving از تغییرهای dataset می‌سازد. هستهٔ آن در `core/lineage.py` است و از دو مدل تشکیل می‌شود: `LineageEvent` برای یک مشاهدهٔ تغییر و `LineageTrail` برای نگهداری رویدادهای مرتب‌شده. اتصال به محصول در `DataManager` انجام شده است؛ بنابراین هر transformationی که از `set_frame` عبور کند، بدون نیاز به instrumentation جداگانه ثبت می‌شود.

این قابلیت برای **provenance در سطح پروژه و DataFrame** طراحی شده است. این نسخه SQL parser، column-expression graph یا dependency بین چند پروژه نیست؛ در عوض یک record قابل‌صادرات از operation، زمان، schema قبل/بعد، تعداد ردیف، source و fingerprint فراهم می‌کند.

## مدل داده و ضمانت privacy

| فیلد | کارکرد | آیا مقدار سلول ذخیره می‌شود؟ |
|---|---|---|
| `sequence` | ترتیب یکتای event در trail | خیر |
| `operation` | برچسب transformation مانند `Renamed amount -> revenue` | خیر |
| `occurred_at` | زمان UTC در قالب ISO-8601 | خیر |
| `input_schema` / `output_schema` | نام ستون، dtype، nullability و fingerprint ساختاری | خیر |
| `input_rows` / `output_rows` | تشخیص اثر row-level transformation | خیر |
| `source` | مسیر یا شناسهٔ source ثبت‌شده در manager | خیر |
| `added_columns` / `removed_columns` / `dtype_changes` | diff محاسبه‌شده از schemaها | خیر |

`capture_schema` تنها metadata ساختاری را به `SchemaSnapshot` تبدیل می‌کند. بنابراین `LineageTrail.to_dict()` نباید name، email، شماره تلفن یا هیچ مقدار خام موجود در rowهای DataFrame را داشته باشد. trail با پیش‌فرض ۲۰۰ رویداد bounded است تا یک پروژه طولانی‌مدت رشد نامحدود نداشته باشد.

## مسیر ثبت خودکار

```python
# core/data_manager.py — مسیر مرکزی همهٔ mutationها

def set_frame(self, frame: pd.DataFrame, label: str) -> None:
    before = self.df.copy() if self.df is not None else None
    self.df = frame.reset_index(drop=True)
    self.lineage.record(label, before, self.df, source=self.source)
    self.history.append(HistoryStep(label, self.df.copy()))
    self.history = self.history[-50:]
    self._redo.clear()
    self.governance_report = None
```

در import، trail reset می‌شود و یک event ریشه تولید می‌گردد. در undo و redo نیز یک event صریح ثبت می‌شود تا audit trail پنهان نکند که analyst به وضعیت قبلی برگشته یا تغییر را دوباره اعمال کرده است.

```python
# core/data_manager.py — ریشهٔ lineage پس از import
self.lineage = LineageTrail()
self.lineage.record("Imported dataset", None, self.df, source=path)
```

## نمونهٔ استفاده از API محصول

نمونهٔ زیر یک manager، تغییر ساختاری و خروجی evidence را نشان می‌دهد. این کد با API موجود DataSense منطبق است.

```python
import pandas as pd
from core.data_manager import DataManager

manager = DataManager(
    df=pd.DataFrame(
        {
            "customer_email": ["alice@example.com", "bob@example.com"],
            "amount": [120, 250],
        }
    ),
    source="memory://sales",
)

# این دو operation هر کدام یک LineageEvent می‌سازند.
manager.rename_column("amount", "revenue")
manager.cast_column("revenue", "numeric")

for event in manager.lineage.events:
    print(event.sequence, event.operation)
    print("added:", event.added_columns)
    print("removed:", event.removed_columns)
    print("dtype changes:", event.dtype_changes)

privacy_safe_evidence = manager.lineage.to_dict()
assert "alice@example.com" not in str(privacy_safe_evidence)
```

خروجی مفهومی این مثال شامل operationهای `Renamed amount -> revenue` و `Cast revenue to numeric`، تغییرهای نام/نوع ستون و row count است؛ emailهای نمونه در evidence وجود ندارند.

## ثبت دستی یک event برای extension اختصاصی

اگر یک plugin یا workspace خارجی بدون فراخوانی `DataManager.set_frame` transformation انجام می‌دهد، باید بعد از ساخت `after` به‌صورت آگاهانه یک event اضافه کند. پلاگین نباید value یا parameter حساس را در `operation` قرار دهد.

```python
before = manager.df.copy()
after = before.assign(revenue_band=pd.cut(before["revenue"], bins=[0, 200, 1000]))

# عنوان operation باید توصیفی و فاقد PII/secret باشد.
manager.df = after.reset_index(drop=True)
manager.lineage.record(
    "Derived revenue band",
    before,
    manager.df,
    source=manager.source,
)
```

برای حفظ سازگاری با undo/redo و history داخلی، extensionهای داخلی محصول باید ترجیحاً به جای assignment مستقیم، `manager.set_frame(after, "Derived revenue band")` را فراخوانی کنند.

## بررسی و export در Trust Center

در رابط Trust Center، دکمهٔ **View lineage** حداکثر پانزده event آخر را نشان می‌دهد. هر سطر شامل شمارهٔ event، operation، زمان، تغییر تعداد ردیف و خلاصهٔ changeهای ستونی است. هنگام **Export audit JSON**، trail کامل در کلید `lineage` وارد evidence می‌شود.

```json
{
  "lineage": {
    "max_events": 200,
    "summary": {
      "event_count": 2,
      "latest_operation": "Cast revenue to numeric"
    },
    "events": [
      {
        "sequence": 1,
        "operation": "Renamed amount -> revenue",
        "added_columns": ["revenue"],
        "removed_columns": ["amount"],
        "dtype_changes": []
      }
    ]
  }
}
```

## ماندگاری پروژه

`core/project.py` trail را در manifest داخلی `.dsproj` ذخیره و در `load_project` بازسازی می‌کند.

```python
# ذخیره
manifest["lineage"] = manager.lineage.to_dict()

# بازیابی
manager.lineage = LineageTrail.from_dict(manifest.get("lineage"))
```

## ارتباط با Schema Drift Guard و Quality Gate

سه کنترل مکمل، اما مستقل هستند. **Lineage Tracker** تاریخچهٔ transform را گزارش می‌کند؛ **Schema Drift Guard** dataset جاری را با baseline ساختاری مقایسه و compatible/blocked تصمیم می‌دهد؛ و **Quality Gate** ruleهای value-level را با score/severity policy ارزیابی می‌کند. blocked شدن Schema Drift به‌تنهایی score quality را تغییر نمی‌دهد، اما هر دو گزارش در export audit قابل اتصال هستند.

| نیاز عملیاتی | قابلیت اصلی |
|---|---|
| «چه کسی و چه operationی schema را تغییر داد؟» | Lineage Tracker به‌علاوهٔ audit actor در Control Plane آینده |
| «آیا dataset فعلی با baseline مجاز است؟» | Schema Drift Guard |
| «آیا مقادیر داده ruleهای کیفیت را رعایت می‌کنند؟» | Data Contract و Quality Gate |
| «چه dashboard یا modelی متاثر می‌شود؟» | roadmap: graph چندپروژه‌ای و impact analysis مرکزی |

## آزمون‌های مربوط

تست `test_lineage_records_schema_only_transformations_and_project_persistence` چهار خاصیت کلیدی را اثبات می‌کند: ثبت rename/cast، نبود emailهای نمونه در evidence، پایداری `.dsproj` و ترتیب operationها پس از restore. اجرای کامل repository پس از rebase نیز **۸۰ passed, 2 warnings** ثبت کرده است؛ warningها از deprecation کتابخانهٔ joblib/NumPy هستند و failure محسوب نمی‌شوند.
