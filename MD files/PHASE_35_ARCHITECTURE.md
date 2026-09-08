# PHASE 35 Architecture — Business Decision Resolution & Workflow Governance

## اصل معماری (بدون تغییر از فاز‌های قبل)
User → Authentication → RBAC+ABAC → Hierarchical Scope → Authorization Engine
→ Request → Domain Service → Domain Model → Domain History → Notification → Audit


**اصل نهایی تثبیت‌شده در این فاز:**
> Request مالک Business Logic دامنه‌ها نیست. Request فقط Orchestrate/Authorize/
> Coordinate/Record/Notify می‌کند. Domain Service مالک Business Rule/State
> Change/Validation/Domain History است.

## چه چیزی در این فاز تغییر کرد

- **هیچ مدل جدیدی ساخته نشد.**
- **هیچ Authorization Engine دومی ساخته نشد.**
- **هیچ Domain موازی (Membership/Role دوم) حذف یا ادغام نشد.**
- فقط ۴ ADR رسماً **تثبیت (RESOLVED)** شدند (۰۱، ۰۴، ۱۱، ۱۲) — چون شواهد کافی و قطعی در Repository برای تصمیم‌گیری وجود داشت.
- ۸ ADR دیگر (۰۲, ۰۳, ۰۵, ۰۶, ۰۷, ۰۸, ۰۹, ۱۰) رسماً **BLOCKED — BUSINESS DECISION REQUIRED** اعلام شدند — چون Repository شواهد کافی برای تصمیم‌گیری بدون حدس نداشت.
- `apps/requests/admin.py::RequestAdmin` سخت‌گیرتر شد (`requester`, `scope` هم به `readonly_fields` اضافه شدند) تا Admin نتواند Workflow را دور بزند.
- تست‌های Governance/Security جدید اضافه شدند (GET Mutation، Privilege Escalation، Status/Approval Field Tampering، Admin Bypass Prevention).

## چرا این رویکرد

طبق قانون قطعی این فاز («عدم اختراع Business Rule»)، تکمیل مصنوعی Integrationهای باقی‌مانده (Membership/Role/Committee/Board) با حدس‌زدن پارامترهای گمشده (مثلاً `new_start_date` برای تمدید عضویت) دقیقاً همان خطایی بود که این فاز باید از آن پرهیز می‌کرد. در عوض، تمرکز روی **رسمی‌سازی معماری موجود** (که قبلاً به‌صورت ضمنی درست کار می‌کرد ولی مستند نشده بود) و **سخت‌گیری امنیتی** (Admin Governance) گذاشته شد — هر دو بدون نیاز به هیچ تصمیم سازمانی جدید.

## معماری نهایی تثبیت‌شده

Request
├── requester, request_type, status, title, description (immutable via Admin)
├── scope (FK AccessScope, immutable via Admin)
├── content_object (GenericForeignKey, Whitelisted — apps/requests/target_validation.py)
├── approved_by, approved_at (فقط از طریق Service Layer)
└── RequestHistory (append-only، read-only در Admin)

Authorization (بدون تغییر):
Authorization.can() + Authorization.scope_queryset() + Resolver Registry + AccessScope

Domain Integration (فقط یک مورد تأییدشده):
Request(EMPLOYMENT_TRANSFER) → apps.employment.services.approve/reject_employment_transfer