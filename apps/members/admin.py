from django.contrib import admin

from apps.authorization.admin_mixins import AuthorizationAdminMixin

from .models import Member, MembershipFee, MembershipPeriod, MembershipStatusHistory


class MembershipPeriodInline(admin.TabularInline):
    model = MembershipPeriod
    extra = 0
    fields = ("start_date", "end_date", "is_active", "reason", "assigned_by")
    autocomplete_fields = ("assigned_by",)


class MembershipStatusHistoryInline(admin.TabularInline):
    """
    فقط‌خواندنی — تغییر status باید همیشه از طریق Service Layer
    (State Machine) انجام شود، نه ویرایش مستقیم در Admin (قانون ۲۳ سند).
    """
    model = MembershipStatusHistory
    extra = 0
    readonly_fields = ("previous_status", "new_status", "actor", "reason", "comment", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Member)
class MemberAdmin(AuthorizationAdminMixin, admin.ModelAdmin):
    view_permission_code = "member.view"
    change_permission_code = "member.update"
    delete_permission_code = "member.delete"

    list_display = ("user", "membership_number", "approval_status", "status")
    list_filter = ("approval_status", "status")
    search_fields = ("user__username", "user__first_name", "user__last_name", "membership_number")
    autocomplete_fields = ("user",)
    readonly_fields = ("status",)
    fields = (
        "user", "membership_number", "registered_by", "approval_status",
        "approved_by", "approved_at", "rejection_reason", "status",
        "legal_decree_file", "network_letter_file",
    )  # تغییر status فقط از طریق Service مجاز است
    inlines = [MembershipPeriodInline, MembershipStatusHistoryInline]


@admin.register(MembershipPeriod)
class MembershipPeriodAdmin(admin.ModelAdmin):
    list_display = ("member", "start_date", "end_date", "is_active")
    list_filter = ("is_active",)
    search_fields = ("member__user__username",)
    autocomplete_fields = ("member", "assigned_by")


@admin.register(MembershipFee)
class MembershipFeeAdmin(admin.ModelAdmin):
    list_display = ("member", "amount", "due_date", "payment_status", "payment_date")
    list_filter = ("payment_status",)
    search_fields = ("member__user__username", "reference_number")
    autocomplete_fields = ("member",)


@admin.register(MembershipStatusHistory)
class MembershipStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("member", "previous_status", "new_status", "actor", "created_at")
    list_filter = ("previous_status", "new_status")
    search_fields = ("member__user__username",)
    readonly_fields = ("member", "previous_status", "new_status", "actor", "reason", "comment", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False