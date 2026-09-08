from django.conf import settings
from django.db import models

from .choices import CommitteeStatus


class Committee(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True)
    purpose = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=CommitteeStatus.choices, default=CommitteeStatus.DRAFT, db_index=True,
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_public_visible = models.BooleanField(
        default=False, db_index=True,
        help_text="آیا این کمیته در صفحه‌ی عمومی کمیته‌ها نمایش داده شود؟",
    )
    scope = models.ForeignKey(
        "authorization.AccessScope", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="committees",
        help_text="محدوده‌ی سازمانی خود کمیته (استان/شهرستان) — مستقل از Scope تخصیص نقش‌ها",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "کمیته"
        verbose_name_plural = "کمیته‌ها"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CommitteeStatusHistory(models.Model):
    committee = models.ForeignKey(Committee, on_delete=models.PROTECT, related_name="status_history")
    previous_status = models.CharField(max_length=20, choices=CommitteeStatus.choices)
    new_status = models.CharField(max_length=20, choices=CommitteeStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="committee_status_changes",
    )
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تاریخچه‌ی وضعیت کمیته"
        verbose_name_plural = "تاریخچه‌های وضعیت کمیته"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.committee} : {self.previous_status} → {self.new_status}"


class CommitteeMembership(models.Model):
    """
    عضویت یک User در یک Committee. تاریخی — رکورد قبلی هرگز حذف
    نمی‌شود، فقط is_active/end_date بسته می‌شود. سمت‌های Chair/Secretary
    این‌جا فیلد نیستند — از RoleAssignment با access_scope.scope_type=
    COMMITTEE استفاده می‌شود (طبق تصمیم معماری فاز ۳۰).
    """

    committee = models.ForeignKey(Committee, on_delete=models.PROTECT, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="committee_memberships"
    )
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_public_visible = models.BooleanField(
        default=False, db_index=True,
        help_text="آیا این عضویت در صفحه‌ی عمومی کمیته نمایش داده شود؟",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="committee_memberships_assigned",
    )
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "عضویت کمیته"
        verbose_name_plural = "عضویت‌های کمیته"
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date")),
                name="committee_membership_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["committee", "user"],
                condition=models.Q(is_active=True),
                name="uniq_active_committee_membership_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user} در {self.committee}"