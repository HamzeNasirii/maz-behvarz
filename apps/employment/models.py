from django.conf import settings
from django.db import models

from apps.authorization.choices import ApprovalStatus

from .choices import EmploymentType
from .managers import EmploymentAssignmentQuerySet


class EmploymentAssignment(models.Model):
    """
    وابستگی هر User به HealthHouse. مستقل از Member — چون
    استخدام و عضویت انجمن دو مفهوم جدا هستند. یک User می‌تواند
    هم‌زمان چند EmploymentAssignment فعال داشته باشد.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="employment_assignments",
    )
    health_house = models.ForeignKey(
        "organization.HealthHouse",
        on_delete=models.PROTECT,
        related_name="employment_assignments",
    )
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.BEHVARZ
    )
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_primary = models.BooleanField(default=False)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employment_assignments_made",
    )
    reason = models.CharField(max_length=255, blank=True)
    approval_status = models.CharField(
        max_length=10, choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING, db_index=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employment_assignments_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EmploymentAssignmentQuerySet.as_manager()

    class Meta:
        verbose_name = "تخصیص محل خدمت"
        verbose_name_plural = "تخصیص‌های محل خدمت"
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date")),
                name="employment_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_primary=True, is_active=True),
                name="uniq_active_primary_employment_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user} @ {self.health_house}"