from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .choices import DocumentStatus, DocumentType, DocumentVisibility
from .validators import ALLOWED_EXTENSIONS


class Document(models.Model):
    """
    سند پیوست‌شده به هر نوع رکورد دیگر (Member، EmploymentAssignment،
    ...) از طریق GenericForeignKey (فاز ۱۶، بدون تغییر). فیلدهای
    visibility/status/scope در فاز ۳۲ اضافه شدند تا این مدل به یک
    سند Domain کامل با Lifecycle و Scope-aware Authorization تبدیل شود
    — بدون ادغام با apps.public_content.PublicDocument (که مفهوم
    متفاوتی دارد: اسناد رسمی سایت عمومی).
    """

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    document_type = models.CharField(max_length=20, choices=DocumentType.choices, db_index=True)
    file = models.FileField(upload_to="documents/%Y/%m/")
    title = models.CharField(max_length=150, blank=True)

    visibility = models.CharField(
        max_length=20, choices=DocumentVisibility.choices, default=DocumentVisibility.PRIVATE, db_index=True,
    )
    status = models.CharField(
        max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.DRAFT, db_index=True,
    )
    scope = models.ForeignKey(
        "authorization.AccessScope", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="documents",
        help_text="محدوده‌ی سازمانی سند (استان/شهرستان/شبکه/مرکز/خانه/کمیته)",
    )

    checksum = models.CharField(max_length=64, blank=True, help_text="SHA-256 فایل")
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=150, blank=True)
    version = models.PositiveIntegerField(default=1)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="documents_uploaded",
    )
    published_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "سند"
        verbose_name_plural = "اسناد"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return self.title or f"{self.get_document_type_display()} — {self.content_object}"


class DocumentStatusHistory(models.Model):
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="status_history")
    previous_status = models.CharField(max_length=20, choices=DocumentStatus.choices)
    new_status = models.CharField(max_length=20, choices=DocumentStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="document_status_changes",
    )
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تاریخچه‌ی وضعیت سند"
        verbose_name_plural = "تاریخچه‌های وضعیت سند"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.document} : {self.previous_status} → {self.new_status}"