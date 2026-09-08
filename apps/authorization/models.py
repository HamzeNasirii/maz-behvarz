from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.organization.models import Province, County, HealthNetwork, HealthCenter, HealthHouse

from .choices import AccessScopeType, ApprovalStatus, RoleAssignmentStatus
from .managers import RoleAssignmentQuerySet


class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True, db_index=True)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مجوز"
        verbose_name_plural = "مجوزها"
        ordering = ["code"]

    def __str__(self):
        return self.code


class Role(models.Model):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "نقش"
        verbose_name_plural = "نقش‌ها"
        ordering = ["code"]

    def __str__(self):
        return self.name


class AccessScope(models.Model):
    """
    Scope اکنون به یک نمونه‌ی مشخص از سلسله‌مراتب سازمانی وصل است.
    طبق قانون ۱۹ سند، از GenericForeignKey استفاده نشده؛ به‌جای آن
    یک FK صریح و nullable برای هر سطح داریم و clean() تضمین می‌کند
    که فقط فیلد متناظر با scope_type مقدار داشته باشد.

    COMMITTEE فعلاً بدون FK است (اپ Committee در گام ۱۴ ساخته می‌شود).
    """

    LEVEL_FIELD_MAP = {
        AccessScopeType.PROVINCE: "province",
        AccessScopeType.COUNTY: "county",
        AccessScopeType.NETWORK: "network",
        AccessScopeType.CENTER: "center",
        AccessScopeType.HOUSE: "house",
        AccessScopeType.COMMITTEE: "committee",
    }
    ALL_LEVEL_FIELDS = ["province", "county", "network", "center", "house", "committee"]

    scope_type = models.CharField(
        max_length=20, choices=AccessScopeType.choices, db_index=True
    )
    province = models.ForeignKey(
        Province, on_delete=models.PROTECT, null=True, blank=True,
        related_name="access_scopes",
    )
    county = models.ForeignKey(
        County, on_delete=models.PROTECT, null=True, blank=True,
        related_name="access_scopes",
    )
    network = models.ForeignKey(
        HealthNetwork, on_delete=models.PROTECT, null=True, blank=True,
        related_name="access_scopes",
    )
    center = models.ForeignKey(
        HealthCenter, on_delete=models.PROTECT, null=True, blank=True,
        related_name="access_scopes",
    )
    house = models.ForeignKey(
        HealthHouse, on_delete=models.PROTECT, null=True, blank=True,
        related_name="access_scopes",
    )
    committee = models.ForeignKey(
        "committees.Committee", on_delete=models.PROTECT, null=True, blank=True,
        related_name="access_scopes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "محدوده‌ی دسترسی"
        verbose_name_plural = "محدوده‌های دسترسی"

    def clean(self):
        required_field = self.LEVEL_FIELD_MAP.get(self.scope_type)

        if required_field:
            if getattr(self, f"{required_field}_id") is None:
                raise ValidationError(
                    {required_field: "این فیلد برای این نوع Scope الزامی است."}
                )
            for field in self.ALL_LEVEL_FIELDS:
                if field != required_field and getattr(self, f"{field}_id") is not None:
                    raise ValidationError(
                        {field: "این فیلد نباید برای این نوع Scope مقدار داشته باشد."}
                    )
        else:
            # GLOBAL, SELF, COMMITTEE — هیچ‌کدام از سطوح سازمانی نباید مقدار داشته باشند
            for field in self.ALL_LEVEL_FIELDS:
                if getattr(self, f"{field}_id") is not None:
                    raise ValidationError(
                        {field: "این فیلد نباید برای این نوع Scope مقدار داشته باشد."}
                    )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def get_health_house_queryset(self):
        """
        QuerySetی از HealthHouseهای درون این Scope. مبنای اصلی
        Hierarchical Access Scope — نمونه‌ی Sari/Babol سند دقیقاً
        همین‌جا پیاده می‌شود.
        """
        if self.scope_type == AccessScopeType.GLOBAL:
            return HealthHouse.objects.all()
        if self.scope_type == AccessScopeType.PROVINCE:
            return HealthHouse.objects.filter(center__network__county__province=self.province)
        if self.scope_type == AccessScopeType.COUNTY:
            return HealthHouse.objects.filter(center__network__county=self.county)
        if self.scope_type == AccessScopeType.NETWORK:
            return HealthHouse.objects.filter(center__network=self.network)
        if self.scope_type == AccessScopeType.CENTER:
            return HealthHouse.objects.filter(center=self.center)
        if self.scope_type == AccessScopeType.HOUSE:
            return HealthHouse.objects.filter(pk=self.house_id)
        # SELF و COMMITTEE در این گام هیچ containment سازمانی‌ای ندارند
        return HealthHouse.objects.none()

    def contains_health_house(self, health_house):
        return self.get_health_house_queryset().filter(pk=health_house.pk).exists()

    def __str__(self):
        target = None
        required_field = self.LEVEL_FIELD_MAP.get(self.scope_type)
        if required_field:
            target = getattr(self, required_field)
        label = self.get_scope_type_display()
        return f"{label} — {target}" if target else label


class RoleAssignment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="role_assignments"
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="assignments")
    access_scope = models.ForeignKey(
        AccessScope, on_delete=models.PROTECT, related_name="role_assignments"
    )
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_assignments_made",
    )
    reason = models.CharField(max_length=255, blank=True)
    approval_status = models.CharField(
        max_length=10, choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING, db_index=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="role_assignments_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)
    is_public_visible = models.BooleanField(
        default=False, db_index=True,
        help_text="آیا این تخصیص نقش (مثلاً نمایندگی) در سایت عمومی نمایش داده شود؟",
    )
    status = models.CharField(
        max_length=20, choices=RoleAssignmentStatus.choices,
        default=RoleAssignmentStatus.ACTIVE, db_index=True,
        help_text="چرخه‌ی عملیاتی تخصیص (Proposed→Active→Ended/Revoked) — مستقل از approval_status",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = RoleAssignmentQuerySet.as_manager()

    class Meta:
        verbose_name = "تخصیص نقش"
        verbose_name_plural = "تخصیص‌های نقش"
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date")),
                name="role_assignment_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.user} → {self.role} ({self.access_scope})"

class RoleAssignmentStatusHistory(models.Model):
    """
    تاریخچه‌ی هر تغییر status روی RoleAssignment — پاسخ به «چه کسی،
    چه چیزی را، چه زمانی و با چه مجوزی تغییر داد؟».
    """

    role_assignment = models.ForeignKey(
        RoleAssignment, on_delete=models.PROTECT, related_name="status_history"
    )
    previous_status = models.CharField(max_length=20, choices=RoleAssignmentStatus.choices)
    new_status = models.CharField(max_length=20, choices=RoleAssignmentStatus.choices)
    actor = models.ForeignKey(
        "accounts.CustomUser", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="role_assignment_status_changes",
    )
    reason = models.CharField(max_length=255, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تاریخچه‌ی وضعیت تخصیص نقش"
        verbose_name_plural = "تاریخچه‌های وضعیت تخصیص نقش"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.role_assignment} : {self.previous_status} → {self.new_status}"