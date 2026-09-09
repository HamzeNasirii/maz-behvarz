from django.db import models

class FeeChangeAction(models.TextChoices):
    EDIT = "edit", "ویرایش"
    DELETE = "delete", "حذف"

class FeePaymentMethod(models.TextChoices):
    CASH = "cash", "نقدی"
    BALE = "bale", "از طریق بله"
    CARD_TO_CARD = "card_to_card", "کارت به کارت"

class FeeChangeStatus(models.TextChoices):
    PENDING = "pending", "در انتظار تصمیم"
    APPROVED = "approved", "تأییدشده"
    REJECTED = "rejected", "ردشده"
    CANCELLED = "cancelled", "انصراف داده‌شده"

class MembershipStatus(models.TextChoices):
    DRAFT = "draft", "پیش‌نویس"
    SUBMITTED = "submitted", "ثبت‌شده"
    UNDER_REVIEW = "under_review", "در حال بررسی"
    APPROVED = "approved", "تأییدشده"
    REJECTED = "rejected", "ردشده"
    ACTIVE = "active", "فعال"
    SUSPENDED = "suspended", "معلق"
    EXPIRED = "expired", "منقضی"
    CANCELLED = "cancelled", "لغوشده"


# قواعد Transition مجاز — طبق بخش ۶ سند. هر تلاش خارج از این نگاشت
# باید مسدود شود.
ALLOWED_TRANSITIONS = {
    MembershipStatus.DRAFT: {MembershipStatus.SUBMITTED},
    MembershipStatus.SUBMITTED: {MembershipStatus.UNDER_REVIEW},
    MembershipStatus.UNDER_REVIEW: {MembershipStatus.APPROVED, MembershipStatus.REJECTED},
    MembershipStatus.APPROVED: {MembershipStatus.ACTIVE},
    MembershipStatus.ACTIVE: {MembershipStatus.SUSPENDED, MembershipStatus.EXPIRED, MembershipStatus.CANCELLED},
    MembershipStatus.SUSPENDED: {MembershipStatus.ACTIVE, MembershipStatus.CANCELLED},
    MembershipStatus.EXPIRED: {MembershipStatus.ACTIVE},
    MembershipStatus.REJECTED: set(),
    MembershipStatus.CANCELLED: set(),
}


class FeePaymentStatus(models.TextChoices):
    UNPAID = "unpaid", "پرداخت‌نشده"
    PAID = "paid", "پرداخت‌شده"
    WAIVED = "waived", "معاف"

class RemovalReason(models.TextChoices):
    NON_PAYMENT = "non_payment", "عدم پرداخت حق عضویت"
    MISCONDUCT = "misconduct", "توهین یا رفتار نامناسب"
    DISCIPLINARY = "disciplinary", "تخلف انضباطی"
    OTHER = "other", "سایر (توضیح در متن)"


class RemovalProposalStatus(models.TextChoices):
    PENDING = "pending", "در انتظار تصمیم"
    APPROVED = "approved", "تأییدشده (عضو حذف شد)"
    REJECTED = "rejected", "ردشده"