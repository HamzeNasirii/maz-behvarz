from django.db import models


class AccessScopeType(models.TextChoices):
    GLOBAL = "global", "سراسری"
    PROVINCE = "province", "استان"
    COUNTY = "county", "شهرستان"
    NETWORK = "network", "شبکه"
    CENTER = "center", "مرکز"
    HOUSE = "house", "خانه بهداشت"
    COMMITTEE = "committee", "کمیته"
    SELF = "self", "شخصی"

class ApprovalStatus(models.TextChoices):
    PENDING = "pending", "در انتظار تأیید"
    APPROVED = "approved", "تأیید شده"
    REJECTED = "rejected", "رد شده"


class RoleAssignmentStatus(models.TextChoices):
    PROPOSED = "proposed", "پیشنهادشده"
    PENDING_APPROVAL = "pending_approval", "در انتظار تأیید"
    ACTIVE = "active", "فعال"
    SUSPENDED = "suspended", "معلق"
    ENDED = "ended", "پایان‌یافته"
    REVOKED = "revoked", "لغوشده (اجباری)"
    REJECTED = "rejected", "ردشده"
    CANCELLED = "cancelled", "لغوشده (داوطلبانه)"


ALLOWED_ROLE_TRANSITIONS = {
    RoleAssignmentStatus.PROPOSED: {RoleAssignmentStatus.PENDING_APPROVAL, RoleAssignmentStatus.CANCELLED},
    RoleAssignmentStatus.PENDING_APPROVAL: {
        RoleAssignmentStatus.ACTIVE, RoleAssignmentStatus.REJECTED, RoleAssignmentStatus.CANCELLED,
    },
    RoleAssignmentStatus.ACTIVE: {RoleAssignmentStatus.SUSPENDED, RoleAssignmentStatus.ENDED, RoleAssignmentStatus.REVOKED},
    RoleAssignmentStatus.SUSPENDED: {RoleAssignmentStatus.ACTIVE, RoleAssignmentStatus.ENDED, RoleAssignmentStatus.REVOKED},
    RoleAssignmentStatus.ENDED: set(),
    RoleAssignmentStatus.REVOKED: set(),
    RoleAssignmentStatus.REJECTED: set(),
    RoleAssignmentStatus.CANCELLED: set(),
}


# طبق بخش ۱۵ سند: هیچ قانون تضاد نقشی بدون Business Rule موجود فرض
# نشده. این دیکشنری عمداً خالی است و فقط نقطه‌ی توسعه‌ی آینده است.
# مثال فرضی (غیرفعال): {"COMMITTEE_MANAGER": {"BOARD_MEMBER"}}
ROLE_CONFLICT_MATRIX = {}