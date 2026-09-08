from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = (
        "برای هر عضو فعال هیئت‌مدیره، یک RoleAssignment واقعی (نقش "
        "BOARD_MEMBER + محدوده‌ی استان مازندران) می‌سازد — طبق قدم اول "
        "طرح مهاجرت از Bypass عمومی هیئت‌مدیره به RBAC+ABAC واقعی. "
        "این دستور Idempotent است (اجرای چندباره مشکلی ایجاد نمی‌کند)."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.authorization.choices import AccessScopeType
        from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
        from apps.board.models import BoardMembership
        from apps.organization.models import Province

        # ۱. پیدا کردن استان مازندران (بدون فرض دقیق بودن املا)
        province = Province.objects.filter(name__icontains="مازندران").first()
        if province is None:
            self.stderr.write(self.style.ERROR(
                "استان «مازندران» در جدول Province پیدا نشد — عملیات متوقف شد."
            ))
            return

        # ۲. نقش BOARD_MEMBER (از فاز ۰۴ از قبل Seed شده)
        try:
            board_role = Role.objects.get(code="BOARD_MEMBER")
        except Role.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                "نقش BOARD_MEMBER در جدول Role پیدا نشد — عملیات متوقف شد."
            ))
            return

        # ۳. اتصال تمام Permissionهای موجود به این نقش — دقیقاً معادل
        # سطح دسترسی فعلی (Bypass عمومی)، این‌بار به‌صورت صریح و واقعی.
        all_permissions = list(Permission.objects.all())
        board_role.permissions.set(all_permissions)
        self.stdout.write(f"تعداد {len(all_permissions)} مجوز به نقش BOARD_MEMBER متصل شد.")

        # ۴. ساخت (یا استفاده از) AccessScope سطح استان مازندران
        province_scope, scope_created = AccessScope.objects.get_or_create(
            scope_type=AccessScopeType.PROVINCE, province=province,
        )
        if scope_created:
            self.stdout.write(f"محدوده‌ی دسترسی جدید برای استان «{province.name}» ساخته شد.")
        else:
            self.stdout.write(f"محدوده‌ی دسترسی موجود برای استان «{province.name}» استفاده شد.")

        # ۵. ساخت RoleAssignment واقعی برای هر عضو فعال هیئت‌مدیره
        active_memberships = BoardMembership.objects.filter(is_active=True).select_related("user")
        created_count = 0
        skipped_count = 0

        for membership in active_memberships:
            already_exists = RoleAssignment.objects.filter(
                user=membership.user, role=board_role, access_scope=province_scope,
            ).exists()
            if already_exists:
                skipped_count += 1
                continue

            RoleAssignment.objects.create(
                user=membership.user, role=board_role, access_scope=province_scope,
                start_date=membership.start_date,
                reason="مهاجرت خودکار از Bypass عمومی هیئت‌مدیره (قدم ۱ اصلاح دسترسی چند‌استانی)",
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"پایان عملیات: {created_count} تخصیص نقش جدید ساخته شد، "
            f"{skipped_count} مورد از قبل موجود بود (رد شد)."
        ))