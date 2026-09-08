from django.db import models


class NotificationType(models.TextChoices):
    MEMBERSHIP_APPROVED = "membership_approved", "تأیید عضویت"
    MEMBERSHIP_REJECTED = "membership_rejected", "رد عضویت"
    EMPLOYMENT_APPROVED = "employment_approved", "تأیید جابه‌جایی محل خدمت"
    EMPLOYMENT_REJECTED = "employment_rejected", "رد جابه‌جایی محل خدمت"
    ROLE_APPROVED = "role_approved", "تأیید تخصیص نقش"
    ROLE_REJECTED = "role_rejected", "رد تخصیص نقش"
    GENERAL = "general", "عمومی"