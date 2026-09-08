from .services import Authorization


class AuthorizationAdminMixin:
    """
    اتصال Django Admin به همان Authorization Engine مرکزی — طبق
    قانون سند که هیچ Authorization جداگانه‌ای نباید در Admin
    ایجاد شود.

    ModelAdminهایی که این Mixin را استفاده می‌کنند باید `view_permission_code`
    و در صورت نیاز `change_permission_code` / `delete_permission_code` را
    تعریف کنند.
    """

    view_permission_code = None
    change_permission_code = None
    delete_permission_code = None

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return Authorization.scope_queryset(request.user, qs)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if not self.view_permission_code:
            return super().has_view_permission(request, obj)
        return Authorization.can(request.user, self.view_permission_code, obj)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        code = self.change_permission_code or self.view_permission_code
        if not code:
            return super().has_change_permission(request, obj)
        return Authorization.can(request.user, code, obj)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        code = self.delete_permission_code or self.view_permission_code
        if not code:
            return super().has_delete_permission(request, obj)
        return Authorization.can(request.user, code, obj)