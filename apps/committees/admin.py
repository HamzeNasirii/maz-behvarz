from django.contrib import admin

from .models import Committee, CommitteeMembership, CommitteeStatusHistory


class CommitteeMembershipInline(admin.TabularInline):
    model = CommitteeMembership
    extra = 0
    fields = ("user", "start_date", "end_date", "is_active", "is_public_visible", "assigned_by", "reason")
    autocomplete_fields = ("user", "assigned_by")


class CommitteeStatusHistoryInline(admin.TabularInline):
    model = CommitteeStatusHistory
    extra = 0
    readonly_fields = ("previous_status", "new_status", "actor", "reason", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Committee)
class CommitteeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "status", "is_active", "is_public_visible")
    search_fields = ("name", "code")
    list_filter = ("status", "is_active", "is_public_visible")
    autocomplete_fields = ("scope",)
    readonly_fields = ("status",)
    inlines = [CommitteeMembershipInline, CommitteeStatusHistoryInline]


@admin.register(CommitteeMembership)
class CommitteeMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "committee", "start_date", "end_date", "is_active", "is_public_visible")
    list_filter = ("is_active", "committee", "is_public_visible")
    search_fields = ("user__username", "committee__name")
    autocomplete_fields = ("committee", "user", "assigned_by")


@admin.register(CommitteeStatusHistory)
class CommitteeStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("committee", "previous_status", "new_status", "actor", "created_at")
    search_fields = ("committee__name",)
    readonly_fields = ("committee", "previous_status", "new_status", "actor", "reason", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False