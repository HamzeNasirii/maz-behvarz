from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .choices import RequestStatus, RequestType


class Request(models.Model):
    """
    Request Domain مرکزی — طبق Audit این فاز، هیچ مدل عمومی مشابهی در
    پروژه وجود نداشت، پس این مدل CREATE شد (نه EXTEND/REUSE). این مدل
    جایگزین هیچ‌کدام از State Machineهای دامنه‌محور موجود (Membership/
    RoleAssignment/Committee/Board/Document) نیست — فقط لایه‌ای عمومی
    برای درخواست‌های اداری/گردش‌کار است که در صورت نیاز (فعلاً فقط
    EMPLOYMENT_TRANSFER) با Service دامنه‌ی واقعی یکپارچه می‌شود.
    """

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requests_created",
    )
    request_type = models.CharField(max_length=30, choices=RequestType.choices, db_index=True)
    status = models.CharField(
        max_length=20, choices=RequestStatus.choices, default=RequestStatus.DRAFT, db_index=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    scope = models.ForeignKey(
        "authorization.AccessScope", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="requests",
        help_text="محدوده‌ی سازمانی درخواست (برای Scope-aware Authorization مدیران)",
    )

    # اتصال اختیاری به یک آبجکت دامنه‌ی واقعی (مثلاً یک EmploymentAssignment
    # در انتظار تأیید) — طبق بخش ۲۷/۴۰ سند، مدل جدید ساخته نشد.
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="requests_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "درخواست"
        verbose_name_plural = "درخواست‌ها"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["requester", "status"]),
            models.Index(fields=["request_type", "status"]),
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.get_request_type_display()} — {self.title} ({self.get_status_display()})"


class RequestHistory(models.Model):
    """
    تاریخچه‌ی تغییر وضعیت — طبق قانون Historical Integrity، هرگز حذف
    یا ویرایش عادی نمی‌شود (در Admin هم read-only است).
    """

    request = models.ForeignKey(Request, on_delete=models.PROTECT, related_name="history")
    from_status = models.CharField(max_length=20, choices=RequestStatus.choices, blank=True)
    to_status = models.CharField(max_length=20, choices=RequestStatus.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="request_status_changes",
    )
    reason = models.CharField(max_length=255, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تاریخچه‌ی وضعیت درخواست"
        verbose_name_plural = "تاریخچه‌های وضعیت درخواست"
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.request} : {self.from_status} → {self.to_status}"