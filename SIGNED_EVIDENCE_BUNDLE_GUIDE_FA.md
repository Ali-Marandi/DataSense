# راهنمای Signed Evidence Bundle در DataSense

## هدف و مرز امنیتی

Signed Evidence Bundle یک فایل JSON قابل‌انتقال است که نتیجهٔ Trust Center را با HMAC-SHA256 امضا می‌کند تا گیرنده بتواند تشخیص دهد payload پس از export تغییر کرده است. Bundle برای audit evidence طراحی شده است، نه برای رمزگذاری dataset، کنترل دسترسی، یا جایگزینی KMS سازمانی.

> Bundle به‌صورت طراحی‌شده مقدار خام dataset، valueهای پارامتر rule، و مسیر local source را نگه نمی‌دارد. با این حال، نام ستون، نام rule، schema fingerprint، تعداد row، metadata کیفیت و transformation metadata ممکن است در محیط شما حساس تلقی شوند. پیش از اشتراک‌گذاری، policy طبقه‌بندی سازمان را اعمال کنید.

## محتوا و ضمانت

| بخش | محتوا | هدف |
|---|---|---|
| `payload` | Contract خلاصه‌شده، report کیفیت، gate، schema drift، history و lineage metadata-only | evidence قابل review بدون کپی دادهٔ خام |
| `payload_sha256` | hash canonical payload | آشکارسازی تغییر payload |
| `signature` | algorithm، key ID و HMAC | اثبات اصالت نسبت به key مشترک |
| `privacy` | تعهد صریح عدم وجود cell value، rule parameter value و source path | مرز قابل‌آزمون برای export |

canonical JSON با sort key و separator ثابت ساخته می‌شود. بنابراین تفاوت ترتیب کلیدهای JSON، digest یا signature را تغییر نمی‌دهد؛ تغییر محتوای payload، verification را fail می‌کند.

## export از Trust Center

پس از اجرای Quality Check، در بخش **Audit evidence** روی **Export signed evidence bundle** کلیک کنید. برنامه ابتدا key file را می‌گیرد و سپس مسیر فایل JSON امضاشده را می‌پرسد. کلید در bundle ذخیره نمی‌شود. Key ID از نام فایل کلید به‌دست می‌آید تا verifier بتواند کلید صحیح را انتخاب کند.

برای یک pilot محلی، security owner باید یک secret تصادفی در secret manager یا vault سازمان بسازد، آن را به‌صورت فایل با permission محدود در اختیار signer بدهد و identifier آن را در key registry ثبت کند. کلید را هرگز در repository، `.dsproj`، ticket، email، log یا خود bundle قرار ندهید.

## verification مستقل

روی سیستمی که کلید مورد تأیید را از مسیر امن دریافت می‌کند، دستور زیر اجرا می‌شود:

```bash
python -m core.evidence path/to/evidence.signed.json --key-file path/to/pilot-hmac.key
```

خروجی JSON شامل `valid`، `reason` و `payload_sha256` است. خروجی معتبر تنها زمانی صادر می‌شود که schema پشتیبانی‌شده باشد، digest canonical برابر باشد، key ID با key مورد انتظار منطبق باشد و HMAC صحیح باشد. برای جلوگیری از انتخاب کلید اشتباه می‌توان key ID مورد انتظار را صریحاً اضافه کرد:

```bash
python -m core.evidence path/to/evidence.signed.json \
  --key-file path/to/pilot-hmac.key \
  --key-id pilot-hmac
```

## چرخهٔ کلید و عملیات

| کنترل | حداقل pilot | production سازمانی |
|---|---|---|
| نگهداری key | فایل permission-limited خارج از repository | KMS/HSM یا secret manager با access policy |
| Key ID | نام غیرمبهم و ثبت‌شده | registry versioned با owner و lifecycle |
| rotation | هنگام تغییر مالک یا incident | rotation policy دوره‌ای و audit evidence |
| verification | دستور محلی و ثبت SHA-256 در ticket | service یا workflow با allow-list key ID |
| revocation | توقف اعتماد به key ID آسیب‌دیده | registry revocation و re-signing policy |

HMAC برای pilot و deployment محلی مناسب است، چون signer و verifier یک secret مشترک دارند. برای اشتراک گسترده با ممیزان خارجی، امضای نامتقارن یا KMS-managed signature مسیر مناسب‌تری است؛ این تغییر تنها پس از تعیین threat model، key ownership و integration سازمان انجام شود.

## معیار پذیرش

یک release سازمانی زمانی می‌تواند این قابلیت را «آماده» معرفی کند که export سالم، verification مستقل، fail شدن verification پس از tamper، عدم وجود raw value در bundle، ثبت key owner و runbook rotation همگی evidence داشته باشند. suite فعلی این رفتارهای cryptographic و privacy boundary را پوشش می‌دهد؛ اتصال KMS و policy registry هنوز scope آینده و وابسته به محیط مشتری است.
