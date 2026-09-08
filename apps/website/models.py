from django.db import models

from apps.authorization.choices import ApprovalStatus


class MembershipApplication(models.Model):
    """
    درخواست عضویت عمومی — قبل از ساخت User/Member واقعی. بررسی و
    تبدیل به عضو رسمی توسط ادمین انجام می‌شود (گام ۱۵: Requests).
    """

    full_name = models.CharField(max_length=150)
    national_code = models.CharField(max_length=10, unique=True, db_index=True)
    mobile_number = models.CharField(max_length=15)
    legal_decree_file = models.FileField(
        upload_to="membership_applications/legal_decree/%Y/%m/",
        verbose_name="آخرین حکم کارگزینی",
        blank=True, null=True,
    )
    network_letter_file = models.FileField(
        upload_to="membership_applications/network_letter/%Y/%m/",
        verbose_name="نامه‌ی ممهور شبکه بهداشت",
        blank=True, null=True,
    )
    accepted_terms = models.BooleanField(default=False, verbose_name="پذیرش تعهدنامه")
    health_house = models.ForeignKey(
        "organization.HealthHouse",
        on_delete=models.PROTECT,
        null=True,
        related_name="membership_applications",
        verbose_name="خانه بهداشت محل خدمت",
    )
    accepted_terms = models.BooleanField(default=False, verbose_name="پذیرش تعهدنامه")
    status = models.CharField(
        max_length=10, choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING, db_index=True,
    )
    reviewed_by = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="membership_applications_reviewed",
    )
    review_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "درخواست عضویت"
        verbose_name_plural = "درخواست‌های عضویت"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.get_status_display()})"
