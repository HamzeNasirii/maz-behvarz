from django.contrib import admin

from .models import Request, RequestHistory


class RequestHistoryInline(admin.TabularInline):
    model = RequestHistory
    extra = 0
    readonly_fields = ("from_status", "to_status", "changed_by", "reason", "changed_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ("title", "request_type", "requester", "status", "created_at")
    list_filter = ("request_type", "status")
    search_fields = ("title", "requester__username")
    autocomplete_fields = ("requester", "scope", "approved_by")
    readonly_fields = (
        "requester", "scope", "status", "approved_by", "approved_at",
        "submitted_at", "completed_at", "cancelled_at",
    )
    inlines = [RequestHistoryInline]


@admin.register(RequestHistory)
class RequestHistoryAdmin(admin.ModelAdmin):
    list_display = ("request", "from_status", "to_status", "changed_by", "changed_at")
    search_fields = ("request__title",)
    readonly_fields = ("request", "from_status", "to_status", "changed_by", "reason", "changed_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False