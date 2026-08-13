# شواهد نهایی: ۸۰ آزمون موفق پس از Data Lineage Tracker

## نتیجهٔ اجرا

فرمان اجراشده:

```bash
python3 -m pytest -q --junitxml=validation_evidence/full_suite_lineage.xml
```

| معیار JUnit | مقدار |
|---|---:|
| Tests | 80 |
| Failures | 0 |
| Errors | 0 |
| Skipped | 0 |
| زمان اجرا | 4.863 ثانیه |
| Warnings | 2 warning غیرمسدودکننده از `joblib.numpy_pickle` دربارهٔ NumPy 2.5 |

## توزیع پوشش

| ماژول | تعداد | دامنه |
|---|---:|---|
| `tests.test_v2_1_engines` | 53 | عملیات و engineهای تحلیل DataManager. |
| `tests.test_governance` | 13 | Data Contract، Quality Gate، PII-safe evidence، Schema Drift و Lineage. |
| `tests.test_import_smoke` | 7 | import/launch رابط PyQt و Trust Center. |
| `enterprise_control_plane.tests.test_security_flow` | 4 | PKCE، RBAC tenant isolation و SAML replay protection. |
| `tests.test_data_manager` | 3 | سازگاری state و عملیات پایهٔ DataManager. |

## افزایش از ۷۹ به ۸۰

افزایش یک test ناشی از case جدید `test_lineage_records_schema_only_transformations_and_project_persistence` است. این case تغییر نام ستون و cast را ثبت می‌کند، اثبات می‌نماید مقدارهای email نمونه وارد evidence lineage نمی‌شوند، و persistence trail را پس از save/load `.dsproj` بررسی می‌کند.

در نتیجه، evidence قبلی ۷۹ test برای Schema Drift Guard معتبر باقی می‌ماند و evidence فعلی ۸۰ test آن را به‌علاوهٔ قابلیت Lineage Tracker پوشش می‌دهد. این نتیجه یک regression proof برای repository است، نه جایگزین Windows artifact smoke، code-signing، security scan یا integration test production با IdP/notification channel.
