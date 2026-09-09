from django.db import models


class DocumentType(models.TextChoices):
    NATIONAL_ID = "national_id", "کارت ملی"
    CERTIFICATE = "certificate", "مدرک تحصیلی"
    CONTRACT = "contract", "قرارداد"
    OTHER = "other", "سایر"


class DocumentVisibility(models.TextChoices):
    PRIVATE = "private", "خصوصی"
    INTERNAL = "internal", "داخلی"
    RESTRICTED = "restricted", "محدود"
    PUBLIC = "public", "عمومی"


class DocumentStatus(models.TextChoices):
    DRAFT = "draft", "پیش‌نویس"
    REVIEW = "review", "در حال بررسی"
    APPROVED = "approved", "تأییدشده"
    PUBLISHED = "published", "منتشرشده"
    ARCHIVED = "archived", "بایگانی‌شده"


ALLOWED_DOCUMENT_TRANSITIONS = {
    DocumentStatus.DRAFT: {DocumentStatus.REVIEW},
    DocumentStatus.REVIEW: {DocumentStatus.APPROVED, DocumentStatus.DRAFT},
    DocumentStatus.APPROVED: {DocumentStatus.PUBLISHED},
    DocumentStatus.PUBLISHED: {DocumentStatus.ARCHIVED},
    DocumentStatus.ARCHIVED: set(),
}