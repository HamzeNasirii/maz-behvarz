# Request → Domain Integration Contract — Phase 35

## قرارداد رسمی (بخش ۱۹ سند)

Request Service (apps/requests/services.py)
→ validate (target_validation.validate_target_object)
→ authorize (Authorization.can / has_permission_code)
→ resolve target (request_obj.content_object)
→ execute domain service (فقط برای EMPLOYMENT_TRANSFER)
→ record RequestHistory (_transition)
→ record Domain History (توسط خود Domain Service، مستقل)
→ notify (send_notification، فقط requester)


## Integration های تأییدشده

### ✅ Request → Employment (تنها Integration فعال)
```python
# apps/requests/services.py::_apply_domain_action_on_approve
if request_obj.request_type == RequestType.EMPLOYMENT_TRANSFER:
    if isinstance(request_obj.content_object, EmploymentAssignment):
        approve_employment_transfer(assignment=request_obj.content_object, approved_by=actor)
```
Request هرگز مستقیماً `EmploymentAssignment.approval_status` را تغییر نمی‌دهد — فقط
Domain Service موجود را فراخوانی می‌کند. `EmploymentAssignment` مالک State/Validation
خودش باقی می‌ماند.

## Integration های BLOCKED (طبق ADR-07 تا ADR-10)

### ❌ Request → Membership
دلیل: `renew_membership()` به `new_start_date` نیاز دارد که در مدل `Request` وجود
ندارد. اضافه‌کردن این پارامتر یا انتخاب یک Default (Business/Architecture Decision)
هردو خارج از این فاز است.

### ❌ Request → RoleAssignment
دلیل: عدم قطعیت Source of Truth (ADR-02). فراخوانی هرکدام از دو مسیر بدون تصمیم
سازمانی، ریسک ناسازگاری داده ایجاد می‌کند.

### ❌ Request → Committee
دلیل: معنای عملیاتی نامشخص — مدل `Request` فیلدی برای «کدام Committee» یا «کدام
Position درخواستی» ندارد.

### ❌ Request → Board
دلیل: مشابه Committee — «کدام Board period» و «کدام Position» در مدل `Request`
قابل‌استخراج نیست.

## نکته‌ی مهم معماری

هیچ‌کدام از این چهار Integration مسدود‌شده به این معنا نیست که خود دامنه‌ها (Membership/
Role/Committee/Board) ناقص‌اند — آن‌ها کاملاً کاربردی و از طریق Admin/Managementهای
اختصاصی خودشان (فازهای ۲۸-۳۱) قابل استفاده‌اند. فقط **اتصال خودکار از طریق Request**
پیاده نشده است.