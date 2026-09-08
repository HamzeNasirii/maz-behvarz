from django.contrib import admin

from .models import Board, BoardMembership, BoardStatusHistory


class BoardMembershipInline(admin.TabularInline):
    model = BoardMembership
    extra = 0
    fields = ("user", "position", "start_date", "end_date", "is_active", "is_public_visible", "assigned_by")
    autocomplete_fields = ("user", "assigned_by")


class BoardStatusHistoryInline(admin.TabularInline):
    model = BoardStatusHistory
    extra = 0
    readonly_fields = ("previous_status", "new_status", "actor", "reason", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "start_date", "end_date", "is_public_visible")
    search_fields = ("name",)
    list_filter = ("status", "is_public_visible")
    readonly_fields = ("status",)
    inlines = [BoardMembershipInline, BoardStatusHistoryInline]


@admin.register(BoardMembership)
class BoardMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "board", "position", "start_date", "end_date", "is_active", "is_public_visible")
    list_filter = ("is_active", "position", "is_public_visible", "board")
    search_fields = ("user__username",)
    autocomplete_fields = ("board", "user", "assigned_by")