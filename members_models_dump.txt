from django.conf import settings
from django.db import models

from apps.authorization.choices import ApprovalStatus

from .choices import FeePaymentStatus, MembershipStatus, RemovalProposalStatus, RemovalReason, FeeChangeStatus, \
    FeeChangeAction, FeePaymentMethod
from .managers import MemberQuerySet, MembershipPeriodQuerySet


class Member(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="member_profile"
    )
    membership_number = models.CharField(
        max_length=20, unique=True, blank=True, null=True, db_index=True
    )
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="members_registered",
    )
    approval_status = models.CharField(
        max_length=10, choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING, db_index=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="members_approved",
    )
    documents_verified_at = models.DateTimeField(null=True, blank=True)
    documents_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="documents_verified",
    )
    legal_decree_approved_at = models.DateTimeField(null=True, blank=True)
    network_letter_approved_at = models.DateTimeField(null=True, blank=True)
    national_id_approved_at = models.DateTimeField(null=True, blank=True)
    birth_certificate_approved_at = models.DateTimeField(null=True, blank=True)
    legal_decree_rejection_reason = models.CharField(max_length=255, blank=True)
    network_letter_rejection_reason = models.CharField(max_length=255, blank=True)
    national_id_rejection_reason = models.CharField(max_length=255, blank=True)
    birth_certificate_rejection_reason = models.CharField(max_length=255, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)

    status = models.CharField(
        max_length=20, choices=MembershipStatus.choices,
        default=MembershipStatus.DRAFT, db_index=True,
        help_text="چرخه‌ی کامل عضویت (پس از پذیرش اولیه) — مستقل از approval_status",
    )
    legal_decree_file = models.FileField(
        upload_to="members/legal_decree/%Y/%m/", blank=True, null=True,
        verbose_name="آخرین حکم کارگزینی",
    )
    network_letter_file = models.FileField(
        upload_to="members/network_letter/%Y/%m/", blank=True, null=True,
        verbose_name="نامه‌ی ممهور شبکه بهداشت",
    )
    national_id_card_file = models.ImageField(
        upload_to="members/national_id/%Y/%m/", blank=True, null=True,
        verbose_name="تصویر کارت ملی",
    )
    mobile_number = models.CharField(max_length=11, blank=True, verbose_name="شماره تماس")
    service_start_date = models.DateField(
        null=True, blank=True, verbose_name="تاریخ شروع به خدمت بهورزی",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MemberQuerySet.as_manager()

    class Meta:
        verbose_name = "عضو"
        verbose_name_plural = "اعضا"
        ordering = ["id"]

    def __str__(self):
        return str(self.user)

    @property
    def years_of_service(self):
        """سال‌های خدمت — محاسبه‌ی زنده (بدون فریز)، بر پایه‌ی تاریخ امروز."""
        if not self.service_start_date:
            return None
        from django.utils import timezone

        today = timezone.localdate()
        years = today.year - self.service_start_date.year
        if (today.month, today.day) < (self.service_start_date.month, self.service_start_date.day):
            years -= 1
        return max(years, 0)


class MembershipPeriod(models.Model):
    """
    تاریخچه‌ی عضویت/پرداخت حق عضویت. هرگز رکورد قبلی حذف نمی‌شود؛
    برای تغییر وضعیت، رکورد جدید ایجاد و رکورد قبلی تاریخی می‌شود.
    """

    member = models.ForeignKey(
        Member, on_delete=models.PROTECT, related_name="membership_periods"
    )
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    reason = models.CharField(max_length=255, blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="membership_periods_assigned",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MembershipPeriodQuerySet.as_manager()

    class Meta:
        verbose_name = "دوره‌ی عضویت"
        verbose_name_plural = "دوره‌های عضویت"
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__isnull=True)
                      | models.Q(end_date__gte=models.F("start_date")),
                name="membership_period_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.member} ({self.start_date} - {self.end_date or 'تاکنون'})"


class MembershipStatusHistory(models.Model):
    """
    تاریخچه‌ی هر تغییر وضعیت عضویت — پاسخ به «چه کسی، چه چیزی را، چه
    زمانی و با چه مجوزی تغییر داد؟» (قانون ۹ سند اصلی).
    """

    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="status_history")
    previous_status = models.CharField(max_length=20, choices=MembershipStatus.choices)
    new_status = models.CharField(max_length=20, choices=MembershipStatus.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="membership_status_changes",
    )
    reason = models.CharField(max_length=255, blank=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تاریخچه‌ی وضعیت عضویت"
        verbose_name_plural = "تاریخچه‌های وضعیت عضویت"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.member} : {self.previous_status} → {self.new_status}"


class MembershipFee(models.Model):
    """
    طبق قانون ۲۰ سند: Payment و Membership Status دو Domain مستقل‌اند.
    ثبت پرداخت این‌جا هرگز مستقیماً status عضو را تغییر نمی‌دهد.
    """

    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="fees")
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    due_date = models.DateField()
    payment_status = models.CharField(
        max_length=10, choices=FeePaymentStatus.choices, default=FeePaymentStatus.UNPAID, db_index=True,
    )
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True, choices=FeePaymentMethod.choices)
    reference_number = models.CharField(max_length=100, blank=True)
    receipt = models.FileField(upload_to="members/fee_receipts/%Y/%m/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "حق عضویت"
        verbose_name_plural = "حق‌های عضویت"
        ordering = ["-due_date"]

    def __str__(self):
        return f"{self.member} — {self.amount} ({self.get_payment_status_display()})"


class MemberRemovalProposal(models.Model):
    """
    هر عضو هیئت‌مدیره (هر ۵ سمت) می‌تواند پیشنهاد حذف بدهد؛ فقط رئیس/
    دبیر می‌توانند تصمیم نهایی بگیرند (طبق تصمیم صریح). تأیید، منجر به
    فراخوانی cancel_membership() موجود می‌شود — نه حذف فیزیکی.
    """

    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="removal_proposals")
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="removal_proposals_made",
    )
    reason = models.CharField(max_length=20, choices=RemovalReason.choices)
    reason_detail = models.CharField(max_length=500, blank=True, help_text="توضیح تکمیلی (الزامی برای «سایر»)")
    status = models.CharField(max_length=10, choices=RemovalProposalStatus.choices,
                              default=RemovalProposalStatus.PENDING)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="removal_proposals_decided",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "پیشنهاد حذف عضو"
        verbose_name_plural = "پیشنهادهای حذف عضو"
        ordering = ["-created_at"]

    def __str__(self):
        return f"پیشنهاد حذف {self.member} — {self.get_status_display()}"


class FeeChangeRequest(models.Model):
    """
    درخواست ویرایش/حذف یک حق عضویت — طبق تصمیم صریح، خزانه‌دار فقط
    می‌تواند «درخواست» بدهد؛ تصمیم نهایی (تأیید/رد) فقط با رئیس،
    نایب‌رئیس یا دبیر است. مسیر کامل (کی درخواست داد، کی تصمیم گرفت)
    حتی بعد از حذف واقعی حق‌عضویت باقی می‌ماند (fee=SET_NULL + Snapshot).
    """

    fee = models.ForeignKey(
        MembershipFee, on_delete=models.SET_NULL, null=True, blank=True, related_name="change_requests",
    )
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="fee_change_requests")
    action = models.CharField(max_length=10, choices=FeeChangeAction.choices)

    # عکس لحظه‌ای مبلغ/تاریخ فعلی در زمان ثبت درخواست — تا حتی بعد از
    # حذف واقعی رکورد Fee، تاریخچه بامعنا و قابل‌پیگیری بماند.
    original_amount = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    original_due_date = models.DateField(null=True, blank=True)

    # فقط برای اکشن EDIT پر می‌شوند
    new_amount = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    new_due_date = models.DateField(null=True, blank=True)

    reason = models.CharField(max_length=500, verbose_name="دلیل درخواست")

    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="fee_change_requests_made",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=10, choices=FeeChangeStatus.choices, default=FeeChangeStatus.PENDING)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="fee_change_requests_decided",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "درخواست اصلاح/حذف حق عضویت"
        verbose_name_plural = "درخواست‌های اصلاح/حذف حق عضویت"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_action_display()} حق عضویت — {self.get_status_display()}"

    @property
    def proposer_role_label(self):
        from apps.board.permissions import get_active_board_position_label

        return get_active_board_position_label(self.proposed_by)

    @property
    def decider_role_label(self):
        from apps.board.permissions import get_active_board_position_label

        return get_active_board_position_label(self.decided_by)

class MemberBirthCertificatePage(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="birth_certificate_pages")
    image = models.ImageField(upload_to="members/birth_certificate/%Y/%m/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تصویر صفحه‌ی شناسنامه"
        verbose_name_plural = "تصاویر صفحات شناسنامه"
        ordering = ["created_at"]

    def __str__(self):
        return f"صفحه‌ی شناسنامه‌ی {self.member} ({self.pk})"