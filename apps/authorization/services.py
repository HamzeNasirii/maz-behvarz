from django.utils import timezone

from .models import RoleAssignment
from .registry import (
    get_object_health_houses,
    get_policy_for,
    get_queryset_scope_resolver,
)


class Authorization:
    """
    لایه‌ی مرکزی Authorization. هیچ View، Admin یا Service دیگری
    نباید مستقیماً RoleAssignment/Permission را چک کند.
    """

    @staticmethod
    def get_active_role_assignments(user, at_date=None):
        if not getattr(user, "is_authenticated", False) or not user.is_active:
            return RoleAssignment.objects.none()
        at_date = at_date or timezone.localdate()
        return RoleAssignment.objects.for_user(user).active().at_date(at_date)

    @classmethod
    def get_permission_codes(cls, user, at_date=None):
        assignments = cls.get_active_role_assignments(user, at_date).select_related("role")
        codes = set()
        for assignment in assignments:
            codes.update(assignment.role.permissions.values_list("code", flat=True))
        return codes

    @classmethod
    def has_permission_code(cls, user, permission_code, at_date=None):
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True
        return permission_code in cls.get_permission_codes(user, at_date)

    @staticmethod
    def _has_delegated_full_access(user):
        """
        دسترسی کامل تفویض‌شده به رئیس/دبیر صنف — طبق تصمیم معماری
        پروژه (چون انجمن فقط یک استان دارد). این Bypass فقط برای
        Permission Check است؛ Scope Containment در can() هنوز جداگانه
        بررسی می‌شود (پایین همین فایل)، مگر این‌که آن‌جا هم Full Access
        باشد.
        """
        if not getattr(user, "is_authenticated", False):
            return False
        try:
            from apps.board.permissions import is_board_member
            return is_board_member(user)
        except Exception:
            return False

    @classmethod
    def can(cls, user, permission_code, obj=None):
        """
        Authorization.can(user, "member.view", member_instance)
        """
        if not cls.has_permission_code(user, permission_code):
            return False

        if obj is None:
            return True

        if not cls._object_in_any_active_scope(user, obj):
            return False

        policy = get_policy_for(obj)
        if policy is not None:
            action = permission_code.split(".")[-1]
            checker = getattr(policy, f"can_{action}", None)
            if checker is not None:
                return checker(user, obj)

        return True

    @classmethod
    def _object_in_any_active_scope(cls, user, obj):
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return True
        houses = get_object_health_houses(obj)
        if houses is None:
            # آبجکتی بدون رزولور تعریف‌شده — فعلاً Scope-aware نیست.
            return True
        if not houses.exists():
            return True

        house_ids = set(houses.values_list("pk", flat=True))
        assignments = cls.get_active_role_assignments(user).select_related("access_scope")
        for assignment in assignments:
            scope_houses = assignment.access_scope.get_health_house_queryset()
            if scope_houses.filter(pk__in=house_ids).exists():
                return True
        return False

    @classmethod
    def scope_queryset(cls, user, queryset):
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return queryset

        resolver = get_queryset_scope_resolver(queryset.model)
        if resolver is None:
            return queryset

        house_ids = set()
        assignments = cls.get_active_role_assignments(user).select_related("access_scope")
        for assignment in assignments:
            house_ids.update(
                assignment.access_scope.get_health_house_queryset().values_list("pk", flat=True)
            )
        if not house_ids:
            return queryset.none()
        return resolver(queryset, house_ids)