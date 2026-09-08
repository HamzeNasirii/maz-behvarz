from django.conf import settings
from django.db import models

from .choices import BoardPosition, BoardStatus


class Board(models.Model):
    """
    دوره‌ی هیئت‌مدیره (مثلاً «هیئت‌مدیره ۱۴۰۴–۱۴۰۶»). این Entity جدید
    (فاز ۳۱) مکمل BoardMembership موجود (فاز ۱۴) است — هرگز جایگزینش
    نمی‌شود.
    """

    name = models.CharField(max_length=150, unique=True)
    description = models.CharField(max_length=255, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    service_start_date = models.DateField(
        null=True, blank=True, verbose_name="تاریخ شروع به خدمت بهورزی",
    )
    status = models.CharField(
        max_length=20, choices=BoardStatus.choices, default=BoardStatus.DRAFT, db_index=True,
    )
    is_public_visible = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "دوره‌ی هیئت‌مدیره"
        verbose_name_plural = "دوره‌های هیئت‌مدیره"
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__isnull=True) | models.Q(end_date__gte=models.F("start_date")),
                name="board_end_after_start",
            ),
        ]

    def __str__(self):
        return self.name


class BoardStatusHistory(models.Model):
    board = models.ForeignKey(Board, on_delete=models.PROTECT, related_name="status_history")
    previous_status = models.CharField(max_length=20, choices=BoardStatus.choices)
    new_status = models.CharField(max_length=20, choices=BoardStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="board_status_changes",
    )
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تاریخچه‌ی وضعیت هیئت‌مدیره"
        verbose_name_plural = "تاریخچه‌های وضعیت هیئت‌مدیره"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.board} : {self.previous_status} → {self.new_status}"


class BoardMembership(models.Model):
    """
    وابستگی هر User به یک دوره‌ی مشخص از Board. فیلد `board` تازه
    اضافه‌شده (nullable، برای سازگاری با رکوردهای قدیمی فاز ۱۴ که
    قبل از وجود مفهوم «دوره» ساخته شده‌اند) — رکوردهای جدید باید
    آن را پر کنند.

    Constraintهای uniqueness عمداً *بدون* board در این فاز باقی
    مانده‌اند (طبق تصمیم معماری مستند در BOARD_REPRESENTATIVE_
    ARCHITECTURE.md) تا رفتار Regression-tested فاز ۱۴ («فقط یک
    رئیس فعال») نشکند.
    """

    board = models.ForeignKey(
        Board, on_delete=models.PROTECT, null=True, blank=True, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="board_memberships"
    )
    position = models.CharField(max_length=20, choices=BoardPosition.choices, db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_public_visible = models.BooleanField(
        default=False, db_index=True,
        help_text="آیا این عضویت در صفحه‌ی عمومی هیئت‌مدیره نمایش داده شود؟",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="board_memberships_assigned",
    )
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "عضویت هیئت‌مدیره"
        verbose_name_plural = "عضویت‌های هیئت‌مدیره"
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__isnull=True)
                      | models.Q(end_date__gte=models.F("start_date")),
                name="board_membership_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_active=True),
                name="uniq_active_board_membership_per_user",
            ),
            models.UniqueConstraint(
                fields=["position"],
                condition=models.Q(is_active=True) & ~models.Q(position="member"),
                name="uniq_active_unique_board_position",
            ),
        ]

    def __str__(self):
        return f"{self.user} — {self.get_position_display()}"
