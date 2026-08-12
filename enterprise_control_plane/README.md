# DataSense Enterprise Control Plane

این پوشه یک سرویس مرجع سازمانی برای **SAML 2.0 SP-initiated SSO**، RBAC چندسازمانی، audit evidence و Quality Gate policy است. برنامهٔ Windows DataSense باید آن را به‌صورت یک public client استفاده کند: مرورگر سیستم را برای ورود باز کند، code کوتاه‌عمر را با PKCE مبادله کند و access token کوتاه‌عمر را فقط در credential store سیستم‌عامل نگه دارد.

## اجزا

| مسیر | مسئولیت |
|---|---|
| `app/saml.py` | ساخت AuthnRequest امضاشده و اعتبارسنجی سخت‌گیرانهٔ ACS با toolkit استاندارد، RelayState و replay protection. |
| `app/auth.py` | authorization code یک‌بارمصرف، PKCE S256 و JWT امضاشده با RS256. |
| `app/rbac.py` | middleware احراز هویت، tenant boundary و dependency مجوز per-action. |
| `app/repositories.py` | adapter PostgreSQL برای اتصال IdP، membership/role resolution و audit events. |
| `schema.sql` | طرح پایدار سازمان، هویت، عضویت، role/permission، SAML و audit با RLS. |
| `config/.env.example` | قرارداد تنظیمات بدون secret واقعی. |

## راه‌اندازی توسعه

محیط توسعه نباید به IdP یا دادهٔ سازمانی واقعی متصل شود. ابتدا virtual environment ایجاد کنید و وابستگی‌ها را نصب نمایید:

```bash
cd enterprise_control_plane
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. pytest -q
```

آزمون‌ها RSA key موقتی تولید می‌کنند و هیچ credential واقعی نیاز ندارند. اجرای کامل ACS در staging مستلزم یک metadata و certificate واقعی برای یک tenant آزمایشی است.

## checklist قبل از production

| الزام | معیار پذیرش |
|---|---|
| Secretها | private key امضای JWT و SAML، HMAC audit و passwordها فقط از KMS/HSM یا mounted secret دریافت شوند. |
| Persistence | PostgreSQL managed و Redis TLSدار با persistence/HA متناسب با RPO/RTO در دسترس باشند. `InMemoryEphemeralStore` مطلقاً production نیست. |
| SAML | metadata IdP خارج از repository تأیید، certificate pin شده، encryption در صورت نیاز، و چهار negative test شامل signature، expiry، destination/audience و replay پاس شده باشد. |
| شبکه | TLS انتهابه‌انتها، reverse proxy مورداعتماد، allowlist proxy، WAF/rate limit و security headers اعمال شده باشد. |
| RBAC | منبع مجوز PostgreSQL باشد، role attribute بدون provisioning صریح پذیرفته نشود، و tenant isolation integration test داشته باشد. |
| عملیات | audit event به SIEM، alert ورود ناموفق/replay/role change، backup و restore تمرینی و runbook incident برقرار باشد. |

## محدودیت‌های آگاهانهٔ نمونهٔ مرجع

کد این پوشه production-oriented است اما صرف وجود آن آماده‌بودن عملیاتی را اثبات نمی‌کند. پیش از اتصال مشتری واقعی، لازم است IaC، migration runner با least privilege، secret manager سازمانی، KMS/HSM، TLS termination، SIEM، test IdP، penetration test و independent security review تکمیل شوند. هیچ کلید، assertion خام، access token یا دادهٔ حساس را در repository، issue یا log قرار ندهید.
