from django.contrib import admin, messages

from .models import MembershipApplication
from .services import approve_membership_application, reject_membership_application


@admin.register(MembershipApplication)
class MembershipApplicationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "national_code", "mobile_number", "health_house", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("full_name", "national_code", "mobile_number")
    autocomplete_fields = ("health_house",)
    readonly_fields = ("created_at", "updated_at", "legal_decree_file", "network_letter_file")
    actions = ["approve_selected_applications", "reject_selected_applications"]

    @admin.action(description="تأیید درخواست‌های انتخاب‌شده و ساخت عضو")
    def approve_selected_applications(self, request, queryset):
        approved_count = 0
        for application in queryset.filter(status="pending"):
            try:
                approve_membership_application(application=application, approved_by=request.user)
                approved_count += 1
            except Exception as exc:
                self.message_user(
                    request, f"خطا در تأیید {application.full_name}: {exc}", level=messages.ERROR
                )
        self.message_user(request, f"{approved_count} درخواست تأیید و عضو ساخته شد.")

    @admin.action(description="رد درخواست‌های انتخاب‌شده")
    def reject_selected_applications(self, request, queryset):
        rejected_count = 0
        for application in queryset.filter(status="pending"):
            reject_membership_application(
                application=application, rejected_by=request.user, note="رد شده توسط ادمین"
            )
            rejected_count += 1
        self.message_user(request, f"{rejected_count} درخواست رد شد.")