from django.contrib import admin

from .models import Permission, Role, AccessScope, RoleAssignment


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")
    ordering = ("code",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    search_fields = ("code", "name")
    list_filter = ("is_active",)
    filter_horizontal = ("permissions",)


@admin.register(AccessScope)
class AccessScopeAdmin(admin.ModelAdmin):
    list_display = ("scope_type", "province", "county", "network", "center", "house")
    list_filter = ("scope_type",)
    search_fields = ("scope_type", "province__name", "county__name", "network__name", "center__name", "house__name")
    autocomplete_fields = ("province", "county", "network", "center", "house")


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "access_scope", "status", "start_date", "end_date", "is_active", "is_public_visible")
    list_filter = ("is_active", "status", "role", "access_scope__scope_type", "is_public_visible")
    search_fields = ("user__username", "role__name")
    autocomplete_fields = ("user", "role", "access_scope", "assigned_by")