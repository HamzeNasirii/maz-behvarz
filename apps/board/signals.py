from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import BoardMembership


@receiver(post_save, sender=BoardMembership)
def ensure_role_assignment_on_board_membership(sender, instance, created, **kwargs):
    """
    هر بار عضویت جدیدی در هیئت‌مدیره فعال شود، خودکار یک RoleAssignment
    واقعی (نقش BOARD_MEMBER + محدوده‌ی استان) برایش ساخته می‌شود — تا
    دیگر نیازی به اجرای دستی sync_board_role_assignments نباشد.
    """
    if not instance.is_active:
        return

    from apps.authorization.choices import AccessScopeType
    from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
    from apps.organization.models import Province

    already_exists = RoleAssignment.objects.filter(
        user=instance.user, role__code="BOARD_MEMBER",
    ).exists()
    if already_exists:
        return

    province = Province.objects.filter(name__icontains="مازندران").first()
    if province is None:
        return

    try:
        board_role = Role.objects.get(code="BOARD_MEMBER")
    except Role.DoesNotExist:
        return

    board_role.permissions.set(Permission.objects.all())

    province_scope, _ = AccessScope.objects.get_or_create(
        scope_type=AccessScopeType.PROVINCE, province=province,
    )
    RoleAssignment.objects.create(
        user=instance.user, role=board_role, access_scope=province_scope,
        start_date=instance.start_date,
        reason="ایجاد خودکار هنگام تخصیص سمت هیئت‌مدیره",
    )