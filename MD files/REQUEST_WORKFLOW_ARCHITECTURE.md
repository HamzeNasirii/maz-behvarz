# Request & Workflow Architecture — Phase 33

## ADR-01: چرا Request Model ایجاد (CREATE) شد؟
هیچ مدل عمومی Request در پروژه وجود نداشت. مدل‌های موجود (Membership/RoleAssignment/
Committee/Board/Document) هرکدام State Machine اختصاصی خودشان را دارند و به‌عمد
تغییر نکردند — Request یک لایه‌ی جدید و عمومی برای درخواست‌های اداری است.

## ADR-02: چرا این Lifecycle؟
دقیقاً طبق بخش ۷ سند: `DRAFT→SUBMITTED→UNDER_REVIEW→APPROVED→COMPLETED` +
شاخه‌های `REJECTED/RETURNED/CANCELLED` + `RESUBMITTED`. هیچ Transition اضافه‌ای
حدس زده نشد.

## ADR-03: Scope چگونه Resolve می‌شود؟
`Request.scope` یک FK صریح به `AccessScope` موجود است (nullable). Resolver جدید
(`request_health_houses`, `scope_request_queryset`) دقیقاً با الگوی Document/
Committee در Registry مرکزی ثبت شد.

## ADR-04: اتصال به Employment/Membership/Role/Board/Committee
فقط `EMPLOYMENT_TRANSFER` به‌صورت خودکار با `approve_employment_transfer`/
`reject_employment_transfer` موجود یکپارچه شد — چون بخش ۴۰ سند صریح و بدون ابهام
بود و فقط یک Service رقیب نداشت. برای `ROLE_ASSIGNMENT`/`COMMITTEE`/`BOARD`/
`MEMBERSHIP` این یکپارچگی **عمداً پیاده نشد** (به دلیل وجود چند سیستم Lifecycle
موازی برای هرکدام در پروژه که انتخاب بین آن‌ها نیازمند تصمیم سازمانی است).

## ADR-05: Notification چگونه Trigger می‌شود؟
فقط به `requester` در Transitionهای approve/reject/return/complete — از طریق
`send_notification()` موجود (فاز ۱۷). Audience سمت Reviewer (چه کسی باید از
ارسال یک درخواست جدید مطلع شود) عمداً Wire نشد — `notify_users_in_scope()`
(فاز ۳۲) به‌عنوان Extension Point در دسترس است.

## ADR-06: جلوگیری از Double Approval
`select_for_update()` روی رکورد Request در ابتدای هر Transition حساس + بررسی
مجدد `ALLOWED_REQUEST_TRANSITIONS` — تلاش دوم برای Approve یک درخواست
APPROVED/COMPLETED با `ValidationError` رد می‌شود (تست‌شده).

## Business Rule Decisions Required
1. Audience اعلان بررسی درخواست (کدام مدیر باید مطلع شود) — نامشخص.
2. یکپارچگی خودکار Request با ROLE_ASSIGNMENT/COMMITTEE/BOARD/MEMBERSHIP —
   نیازمند انتخاب بین سیستم‌های Lifecycle موازی موجود در هر دامنه.
3. Assignment مفهوم `assigned_to` (بخش ۳۲ سند) — پیاده نشد چون Business Rule
   صریحی برای الزامی‌بودنش وجود نداشت.
4. محدودیت ارسال درخواست تکراری (بخش ۴۸ سند) — Constraint مصنوعی ایجاد نشد.

## Known Issues
هیچ‌کدام.

## Technical Debt
- `scope_request_queryset` با Python-side iteration (همان الگوی شناخته‌شده‌ی
  Document/Committee/RoleAssignment).
- Search/Filter پیشرفته (بخش ۲۴ سند: Search, Filter by date, Sorting) فقط در حد
  List ساده پیاده شد؛ فیلترهای پیشرفته در فاز‌های بعدی UI اضافه می‌شوند.