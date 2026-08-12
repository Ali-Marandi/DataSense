# گزارش اعتبارسنجی DataSense

**تاریخ اجرا:** ۱۳ اوت ۲۰۲۶  
**محیط:** Ubuntu sandbox، Python 3.12، PyQt6، pytest  
**Commit مبنا:** `4f45e79` به‌علاوهٔ اصلاح bootstrap headless PyQt در این تغییرات

## نتیجهٔ اجرایی

سه سطح اعتبارسنجی ثبت شد. مجموعهٔ هدفمند امنیت، Quality Gate و رگرسیون محصول شامل **۷۰ آزمون موفق** و دو warning غیرمسدودکننده از `joblib` بود. پس از تثبیت backend headless Qt، suite کامل پایه **۷۷ آزمون موفق** داشت. پس از افزودن Schema Drift Guard و دو آزمون جدید آن، suite نهایی شامل **۷۹ آزمون موفق** و همان دو warning غیرمسدودکننده شد. هیچ failure، error یا skipped test در اجرای نهایی ثبت نشد.

| اجرا | فرمان | نتیجه | شواهد |
|---|---|---:|---|
| Security + Quality Gate + regression | `python3 -m pytest -vv --junitxml=... tests/test_data_manager.py tests/test_governance.py tests/test_v2_1_engines.py enterprise_control_plane/tests/test_security_flow.py` | 70 passed، 2 warnings، 3.34s | `security_quality_regression.log` و `security_quality_regression.xml` |
| PyQt smoke در حالت پایدار | `python3 -m pytest -q tests/test_import_smoke.py` | 7 passed، 4.03s | `pyqt_smoke_stable.log` |
| Full suite پایه پس از رفع PyQt | `python3 -m pytest -q --junitxml=validation_evidence/full_suite_stable.xml` | 77 passed، 2 warnings، 4.92s | `full_suite_stable.log` و `full_suite_stable.xml` |
| Full suite نهایی پس از Schema Drift Guard | `python3 -m pytest -q --junitxml=validation_evidence/full_suite_schema_drift.xml` | 79 passed، 2 warnings، 4.95s | `full_suite_schema_drift.log` و `full_suite_schema_drift.xml` |

## جزئیات ۷۰ آزمون موفق

| حوزه | تعداد | پوشش دقیق |
|---|---:|---|
| موتورهای محصول v2.1 | 53 | APIهای DataManager، transform/undo/redo، import/export، profiling، health score، SQL امن، time-series، model roundtrip، dashboard export و policyهای داده. |
| Trust Center و Quality Gate | 10 | قرارداد داده، score وزن‌دار، عدم جهش داده، PII metadata-only scan، recommended rules، invalidate شدن report قدیمی، persistence پروژه، Quality Gate critical/score، QualityHistory trend و persistence policy/history. |
| DataManager پایه | 3 | رفتار مدیریت داده و سازگاری APIهای core. |
| کنترل‌پلین سازمانی | 4 | authorization code تک‌مصرف، PKCE S256، رد verifier نادرست، tenant isolation با پاسخ 404 و audit denial، تنظیم سخت‌گیرانهٔ SAML و رد replay assertion. |

### پوشش امنیت و Quality Gate

| شناسه آزمون | آنچه اثبات می‌کند | نتیجه |
|---|---|---|
| `test_contract_reports_each_rule_without_mutating_data` | ruleهای not-null، unique، range، allowed-values و regex بدون تغییر dataset اجرا می‌شوند؛ critical failure وضعیت blocked می‌دهد. | Pass |
| `test_empty_contract_does_not_claim_a_perfect_score` | قرارداد خالی score جعلی 100٪ یا trust status ندارد. | Pass |
| `test_sensitive_data_scan_retains_only_metadata` | scan محلی PII مقدار مشاهده‌شده را در finding نگه نمی‌دارد. | Pass |
| `test_manager_invalidates_stale_report_after_mutation` | پس از mutation، report قدیمی بی‌اعتبار می‌شود. | Pass |
| `test_quality_gate_blocks_low_score_and_critical_failure` | gate، critical failure و score کمتر از policy را block می‌کند. | Pass |
| `test_quality_history_tracks_only_quality_metadata_and_direction` | history فقط metadata کیفیت را ذخیره می‌کند و trend improving را محاسبه می‌نماید. | Pass |
| `test_project_round_trip_keeps_quality_policy_and_history` | `.dsproj` policy و history کیفیت را بدون report stale بازیابی می‌کند. | Pass |
| `test_authorization_code_requires_matching_pkce_and_is_single_use` | authorization code فقط با PKCE درست مبادله می‌شود و بار دوم نامعتبر است. | Pass |
| `test_authorization_code_rejects_wrong_pkce_verifier` | verifier متفاوت با challenge S256 رد می‌شود. | Pass |
| `test_permission_service_hides_cross_tenant_resource_and_audits_denial` | resource سازمان دیگر به 404 تبدیل و deny event ممیزی می‌شود. | Pass |
| `test_saml_acs_uses_strict_toolkit_configuration_and_rejects_assertion_replay` | strict mode، پیام/assertion امضاشده، encryption موردنیاز و replay protection فعال هستند. | Pass |

فهرست نام تمام ۷۰ case موفق در `passed_test_cases.txt` و جزئیات خروجی pytest در `security_quality_regression.log` نگهداری می‌شود.

## علت crash باینری PyQt و اصلاح اعمال‌شده

اجرای اولیهٔ `python3 -m pytest -q` با `Fatal Python error: Aborted` خاتمه یافت. علت، انتخاب پیش‌فرض platform plugin مبتنی بر display در runner لینوکسی بود؛ محیط sandbox یک مقدار `DISPLAY` غیرقابل‌اتکا داشت ولی display server قابل استفاده نداشت. اجرای همان suite با `QT_QPA_PLATFORM=offscreen` موفق شد و فرضیه را تأیید کرد.

فایل ریشهٔ `conftest.py` پیش از import هر ماژول PyQt بارگذاری می‌شود و در Linux، backend پیش‌فرض تست را به `offscreen` تغییر می‌دهد. به این ترتیب testها window قابل‌مشاهده نیاز ندارند و CI/headless بدون export دستی متغیر محیطی پایدار اجرا می‌شود. برای diagnosis تعاملی، توسعه‌دهنده می‌تواند پیش از pytest متغیر `DATASENSE_QT_TEST_PLATFORM=xcb` یا platform دیگر را صریحاً تعیین کند.

| حالت | دستور پیشنهادی |
|---|---|
| CI یا Linux headless | `python3 -m pytest -q` |
| اجرای دستی با platform مشخص | `DATASENSE_QT_TEST_PLATFORM=offscreen python3 -m pytest -q` |
| تحلیل plugin Qt | `QT_DEBUG_PLUGINS=1 QT_QPA_PLATFORM=offscreen python3 -m pytest -q tests/test_import_smoke.py -s` |
| اجرای full suite با JUnit evidence | `python3 -m pytest -q --junitxml=validation_evidence/full_suite.xml` |

## Schema Drift Guard در suite نهایی

دو آزمون جدید، تشخیص تغییرهای breaking در dtype/nullability و ماندگاری baseline/policy در `.dsproj` را پوشش می‌دهند. Guard به‌صورت پیش‌فرض افزودن ستون را مجاز، اما حذف ستون، تغییر dtype و nullable شدن ستون قبلاً non-null را block می‌کند. مالک داده می‌تواند policy را به‌صورت صریح تغییر دهد و همان policy همراه پروژه ذخیره می‌شود.

## Warningهای باقی‌مانده

دو warning از `joblib.numpy_pickle` در test model roundtrip دربارهٔ deprecation تغییر shape آرایه در NumPy 2.5 ثبت شد. این warningها failure نیستند و اجرای ۷۹ test نهایی را مختل نکردند. برای کاهش noise آینده، وابستگی‌های scikit-learn/joblib باید در یک maintenance change به نسخهٔ سازگار با NumPy جاری ارتقا یابند و همان test model roundtrip دوباره اجرا شود.
