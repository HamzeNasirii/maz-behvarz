# Workflow Governance — Phase 35

## Reviewer Eligibility (ADR-04 — RESOLVED)

Reviewer Eligible
⟺ user.is_authenticated
AND Authorization.has_permission_code(user, "<request.action>")
AND Authorization.can(user, "<request.action>", request_obj) [Scope Containment]

«داشتن حساب کاربری» به‌تنهایی هرگز کافی نیست — این در تمام View‌های `apps/requests/views.py`
اعمال می‌شود.

## Concurrency Policy (ADR-11 — RESOLVED)

هر Transition حساس (`approve`, `reject`, `return`, `complete`, `cancel`) از این الگو پیروی می‌کند:
```python
request_obj = Request.objects.select_for_update().get(pk=request_obj.pk)
# سپس اعتبارسنجی ALLOWED_REQUEST_TRANSITIONS قبل از هر Mutation
```
نتیجه: تلاش دوم برای Approve یک درخواست تکمیل‌شده، `ValidationError` می‌گیرد، نه
اجرای دوباره‌ی Domain Action (تست‌شده در فاز ۳۴).

## Domain History Contract (ADR-12 — RESOLVED)

هر تغییر وضعیت در هر دامنه (Request/Membership/RoleAssignment/Committee/Board/Document)
این اطلاعات را ثبت می‌کند:

