from django.db import models


class RequestType(models.TextChoices):
    MEMBERSHIP = "membership", "درخواست عضویت"
    MEMBERSHIP_RENEWAL = "membership_renewal", "تمدید عضویت"
    EMPLOYMENT_TRANSFER = "employment_transfer", "تغییر محل خدمت"
    EMPLOYMENT_UPDATE = "employment_update", "اصلاح اطلاعات محل خدمت"
    ROLE_ASSIGNMENT = "role_assignment", "تخصیص نقش انجمنی"
    ROLE_REVOCATION = "role_revocation", "لغو نقش انجمنی"
    COMMITTEE = "committee", "درخواست مربوط به کمیته"
    BOARD = "board", "درخواست مربوط به هیئت‌مدیره"
    DOCUMENT = "document", "درخواست مربوط به اسناد"
    PROFILE_UPDATE = "profile_update", "اصلاح اطلاعات پروفایل"
    OTHER = "other", "سایر"


class RequestStatus(models.TextChoices):
    DRAFT = "draft", "پیش‌نویس"
    SUBMITTED = "submitted", "ثبت‌شده"
    UNDER_REVIEW = "under_review", "در حال بررسی"
    APPROVED = "approved", "تأییدشده"
    REJECTED = "rejected", "ردشده"
    RETURNED = "returned", "برگشت‌داده‌شده"
    RESUBMITTED = "resubmitted", "ثبت‌مجدد"
    CANCELLED = "cancelled", "لغوشده"
    COMPLETED = "completed", "تکمیل‌شده"


# طبق بخش ۷ سند: فقط Transitionهای صریح ذکرشده — هیچ Transition دیگری
# بدون Business Rule اضافه نشده است.
ALLOWED_REQUEST_TRANSITIONS = {
    RequestStatus.DRAFT: {RequestStatus.SUBMITTED, RequestStatus.CANCELLED},
    RequestStatus.SUBMITTED: {RequestStatus.UNDER_REVIEW, RequestStatus.REJECTED, RequestStatus.CANCELLED},
    RequestStatus.UNDER_REVIEW: {
        RequestStatus.APPROVED, RequestStatus.REJECTED, RequestStatus.RETURNED, RequestStatus.CANCELLED,
    },
    RequestStatus.APPROVED: {RequestStatus.COMPLETED},
    RequestStatus.REJECTED: {RequestStatus.RESUBMITTED},
    RequestStatus.RETURNED: {RequestStatus.RESUBMITTED},
    RequestStatus.RESUBMITTED: {RequestStatus.UNDER_REVIEW},
    RequestStatus.CANCELLED: set(),
    RequestStatus.COMPLETED: set(),
}