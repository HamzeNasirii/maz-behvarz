from django.contrib import admin

from apps.authorization.admin_mixins import AuthorizationAdminMixin

from .models import EmploymentAssignment


@admin.register(EmploymentAssignment)
class EmploymentAssignmentAdmin(AuthorizationAdminMixin, admin.ModelAdmin):
    view_permission_code = "employment.view"
    change_permission_code = "employment.update"
    delete_permission_code = "employment.delete"

    list_display = (
        "user", "health_house", "employment_type",
        "start_date", "end_date", "is_active", "is_primary", "approval_status",
    )
    list_filter = ("is_active", "is_primary", "employment_type", "health_house", "approval_status")
    search_fields = ("user__username", "health_house__name")
    autocomplete_fields = ("user", "health_house", "assigned_by")