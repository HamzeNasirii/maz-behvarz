# Business Decisions — Phase 35

## Business Decision Matrix

| Decision | Status | Evidence | Final Decision | ADR |
|---|---|---|---|---|
| Reviewer Assignment | بدون شاهد در Repository | هیچ مدل/فیلد `assigned_to` در هیچ‌جای پروژه یافت نشد | BLOCKED | ADR-03 |
| Reviewer Eligibility | شواهد کامل و قطعی از فاز ۰۶ به بعد | `Authorization.has_permission_code()` + `Authorization.can()` (Scope Containment) در همه‌ی View‌های مدیریتی Request استفاده می‌شود | **RESOLVED** | ADR-04 |
| Notification Audience (Requester) | شواهد کامل از فاز ۱۷/۳۳ | `send_notification()` فقط به `request_obj.requester` صدا زده می‌شود، تست‌شده | **RESOLVED (بخشی)** | ADR-05 |
| Notification Audience (Reviewer/Scope Manager) | بدون شاهد | `notify_users_in_scope()` (فاز۳۲) هرگز از هیچ View‌ای صدا زده نشده | BLOCKED | ADR-05 |
| Duplicate Request Policy | بدون شاهد | هیچ Constraint/Validation/تست مربوط به تکراری‌بودن در `apps/requests/` یافت نشد | BLOCKED (وضعیت فعلی ضمنی: ALLOW) | ADR-06 |
| Membership Source of Truth | شواهد کامل — چهار مفهوم متعامد و بدون هم‌پوشانی کد | `approval_status`≠`status`≠`MembershipPeriod`≠`MembershipFee`؛ تست `test_payment_does_not_change_membership_status` این استقلال را تضمین می‌کند | **RESOLVED** | ADR-01 |
| Role Source of Truth | شواهد تعارض واقعی — دو مسیر UI زنده هردو یک رکورد را می‌نویسند | `pending_roles_view`→`role_services.py`؛ `roles:approve`→`role_lifecycle_services.py` | BLOCKED | ADR-02 |
| Request→Membership | Source حل شد اما پارامتر لازم (`new_start_date`) در مدل Request وجود ندارد | `renew_membership()` نیازمند تاریخی است که هیچ فیلدی در `Request` آن را حمل نمی‌کند | BLOCKED | ADR-07 |
| Request→Role | وابسته به ADR-02 حل‌نشده | — | BLOCKED | ADR-08 |
| Request→Committee | معنای عملیاتی نامشخص (عضویت؟ کدام کمیته؟ کدام سمت؟) | `Request` مدل هیچ فیلدی برای «کدام کمیته/سمت» ندارد | BLOCKED | ADR-09 |
| Request→Board | همان دلیل بالا، برای Board | — | BLOCKED | ADR-10 |
| Concurrency Policy | شواهد کامل و یکنواخت در همه‌ی دامنه‌ها | `select_for_update()` + اعتبارسنجی State Machine قبل از هر Mutation | **RESOLVED** | ADR-11 |
| Domain History Contract | شواهد کامل و یکنواخت | الگوی `*StatusHistory(from_status, to_status, actor, reason, changed_at)` در ۶ دامنه تکرار شده | **RESOLVED** | ADR-12 |

## قوانین حاکم (بدون تغییر و رعایت‌شده)

```
NO SECOND AUTHORIZATION ENGINE       ✅ رعایت شد
NO SECOND MEMBERSHIP SYSTEM           ✅ رعایت شد (هیچ ادغامی انجام نشد)
NO THIRD ROLE SYSTEM                  ✅ رعایت شد
NO PARALLEL REQUEST MODEL             ✅ رعایت شد
NO DUPLICATE DOMAIN MODELS            ✅ رعایت شد
NO BUSINESS RULE INVENTION            ✅ رعایت شد
NO DIRECT MODEL MUTATION FROM VIEW    ✅ رعایت شد
NO GET STATE MUTATION                 ✅ تست شد (test_get_request_to_approve_url_does_not_mutate_state)
NO UNCONTROLLED ADMIN BYPASS          ✅ رفع شد (readonly_fields گسترش یافت)
NO SCOPE BYPASS                       ✅ بدون تغییر، تست‌شده
NO TENANT BYPASS                      N/A (تک‌مستأجری)
NO ARTIFICIAL UNIQUE CONSTRAINT       ✅ رعایت شد (ADR-06 بدون Constraint ماند)
NO BLIND DATA MIGRATION               ✅ هیچ Migration داده‌ای لازم نبود
NO BULK TRANSITION WITHOUT RULE       ✅ رعایت شد (Bulk پیاده نشد)
NO BREAKING CHANGE WITHOUT AUDIT      ✅ رعایت شد
```

