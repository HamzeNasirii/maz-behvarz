# Request Workflow Operations — Phase 34

## ADR-01: Assignment
BLOCKED. هیچ Business Rule سازمانی برای «چه کسی باید Reviewer یک درخواست خاص
باشد» وجود نداشت. `assigned_to` ساخته نشد.

## ADR-02: Reviewer Resolution
BLOCKED (وابسته به ADR-01).

## ADR-03: Notification Audience
BLOCKED. فقط requester مطلع می‌شود (بدون تغییر نسبت به فاز ۳۳).
`notify_users_in_scope()` هنوز Extension Point بدون Wiring است.

## ADR-04: Role Lifecycle Source of Truth
مشخص نشد — پروژه دو سیستم موازی دارد (`role_services.py` مبتنی بر
`approval_status`، `role_lifecycle_services.py` مبتنی بر `status` State
Machine). بدون Business Decision، هیچ‌کدام انتخاب/حذف نشدند.
همین ابهام برای Membership (سه سیستم موازی) هم صادق است.

## ADR-05: اتصال Request به Domainها
فقط `EMPLOYMENT_TRANSFER` (از فاز ۳۳) — Audit مجدد در این فاز تأیید کرد:
Double Execution از طریق State Machine خود Request مسدود می‌شود (چون بعد از
APPROVED دیگر امکان approve مجدد نیست)، History درست ثبت می‌شود.
Committee/Board با اینکه هرکدام یک Service واحد (بدون تعارض) دارند، اتصال
نشدند چون معنی دقیق «تأیید یک Request کمیته/هیئت‌مدیره» (کدام کمیته؟ کدام
Position؟) بدون تصمیم سازمانی مشخص نیست.

## ADR-06: Generic Relation Security
Whitelist صریح از مدل‌های مجاز (`Member, EmploymentAssignment, RoleAssignment,
Committee, CommitteeMembership, Board, BoardMembership, Document`) در
`target_validation.py`. چون فرم عمومی (`RequestCreateForm`) از ابتدا هیچ فیلد
`content_type`/`object_id` را Expose نمی‌کند، این Validation یک لایه‌ی دفاعی
اضافه (Defense in Depth) برای فراخوانی مستقیم Service است.

## ADR-07: Concurrency
بدون تغییر نسبت به فاز ۳۳ (`select_for_update()` + State Machine). Idempotency
تأیید شد: تلاش دوم برای یک Transition نامعتبر هیچ رکورد History جعلی نمی‌سازد
چون اعتبارسنجی (`ALLOWED_REQUEST_TRANSITIONS`) قبل از ساخت `RequestHistory`
انجام می‌شود.

## Queue
فقط Queueهای مستقل از Assignment پیاده شدند: Pending Review، Recently
Returned، Recently Rejected، Recently Completed — همگی Scope-aware (از
`requests_for_management()` که خودش `Authorization.scope_queryset` را صدا
می‌زند). «Assigned to Me»/«Unassigned» به دلیل ADR-01 پیاده نشدند.

## Search/Filter
ترتیب اجباری طبق سند رعایت شد: Scope (`requests_for_management`) → Filter/Search
(`filter_requests`) → Sort (`sort_requests`, whitelist شده) → Pagination
(`Paginator`). تست شد که Search/Pagination نمی‌توانند از Scope عبور کنند.

## Business Decisions Required (منتقل‌شده از فاز ۳۳ + بدون تغییر)
1. Notification Audience برای Reviewer
2. Request → RoleAssignment (کدام سیستم Source of Truth است؟)
3. Request → Committee (معنای دقیق تأیید چیست؟)
4. Request → Board (معنای دقیق تأیید چیست؟)
5. Request → Membership (کدام‌یک از سه سیستم موازی؟)
6. مفهوم `assigned_to`
7. سیاست جلوگیری از درخواست تکراری

## Technical Debt
- `scope_request_queryset` همچنان Python-side iteration است.
- Bulk Operations پیاده نشدند (طبق تصریح صریح سند: «بدون Business Rule، NO BULK
  TRANSITIONS»).
- Outbox Pattern بررسی و **عمداً ایجاد نشد** (طبق دستور صریح سند).