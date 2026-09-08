"""
⚠️ فقط برای محیط توسعه — داده‌ی نمونه برای تست سریع، بدون نیاز به
ورود دستی از طریق رابط کاربری. هرگز روی Production اجرا نشود.
"""
import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


class Command(BaseCommand):
    help = "⚠️ فقط Dev: ساخت سریع ساختار سازمانی + هیئت‌مدیره + چند عضو نمونه برای تست."

    @transaction.atomic
    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model

        from apps.authorization.choices import AccessScopeType
        from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
        from apps.board.choices import BoardPosition
        from apps.board.models import Board, BoardMembership
        from apps.employment.models import EmploymentAssignment
        from apps.members.models import Member, MembershipFee
        from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province
        from apps.organization.scope_sync import ensure_access_scope_for

        User = get_user_model()

        # ۱. ساختار سازمانی
        province, _ = Province.objects.get_or_create(name="مازندران")
        ensure_access_scope_for("province", province)

        county, _ = County.objects.get_or_create(province=province, name="ساری")
        ensure_access_scope_for("county", county)

        network, _ = HealthNetwork.objects.get_or_create(county=county, name="شبکه بهداشت و درمان ساری")
        ensure_access_scope_for("network", network)

        center, _ = HealthCenter.objects.get_or_create(network=network, name="مرکز خدمات جامع سلامت شماره یک")
        ensure_access_scope_for("center", center)

        house, _ = HealthHouse.objects.get_or_create(center=center, name="خانه بهداشت نمونه")
        ensure_access_scope_for("house", house)

        self.stdout.write(self.style.SUCCESS("ساختار سازمانی ساخته شد."))

        # ۲. ادمین (Superuser) — اگر از قبل نبود
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(username="admin", password="admin12345", email="admin@example.com")
            self.stdout.write(self.style.SUCCESS("کاربر ادمین ساخته شد — نام‌کاربری: admin / رمز: admin12345"))

        # ۳. اعضای هیئت‌مدیره (همه‌ی سمت‌ها)
        board, _ = Board.objects.get_or_create(name="دوره ۱", defaults={"start_date": timezone.localdate()})

        board_people = [
            ("1111111111", "رئیس", "انجمن", BoardPosition.CHAIRMAN),
            ("2222222222", "نایب‌رئیس", "انجمن", BoardPosition.VICE_CHAIRMAN),
            ("3333333333", "دبیر", "انجمن", BoardPosition.SECRETARY),
            ("4444444444", "خزانه‌دار", "انجمن", BoardPosition.TREASURER),
            ("5555555555", "عضو", "هیئت‌مدیره", BoardPosition.MEMBER),
        ]

        for national_code, first_name, last_name, position in board_people:
            user, created = User.objects.get_or_create(
                username=national_code,
                defaults={"first_name": first_name, "last_name": last_name},
            )
            if created:
                user.set_password(national_code)
                user.save()

            member, _ = Member.objects.get_or_create(
                user=user, defaults={"approval_status": "approved", "status": "active"},
            )
            EmploymentAssignment.objects.get_or_create(
                user=user, health_house=house, is_primary=True,
                defaults={"start_date": timezone.localdate(), "is_active": True},
            )
            BoardMembership.objects.get_or_create(
                board=board, user=user, position=position,
                defaults={"start_date": timezone.localdate(), "is_active": True},
            )
            self.stdout.write(self.style.SUCCESS(f"{first_name} {last_name} ({national_code}) — {position} ساخته شد."))

        # ۴. چند عضو معمولی (بهورز)
        regular_members = [
            ("6666666666", "زینب", "ابراهیمی"),
            ("7777777777", "علی", "رضایی"),
            ("8888888888", "فاطمه", "الهی"),
        ]
        for national_code, first_name, last_name in regular_members:
            user, created = User.objects.get_or_create(
                username=national_code,
                defaults={"first_name": first_name, "last_name": last_name},
            )
            if created:
                user.set_password(national_code)
                user.save()

            member, _ = Member.objects.get_or_create(
                user=user, defaults={"approval_status": "approved", "status": "active"},
            )
            EmploymentAssignment.objects.get_or_create(
                user=user, health_house=house, is_primary=True,
                defaults={"start_date": timezone.localdate(), "is_active": True},
            )
            behvarz_role = Role.objects.filter(code="BEHVARZ").first()
            if behvarz_role:
                house_scope, _ = AccessScope.objects.get_or_create(scope_type=AccessScopeType.HOUSE, house=house)
                RoleAssignment.objects.get_or_create(
                    user=user, role=behvarz_role, access_scope=house_scope,
                    defaults={"start_date": timezone.localdate()},
                )

            # یک حق‌عضویت نمونه برای هرکدام
            MembershipFee.objects.get_or_create(
                member=member, due_date=timezone.localdate() + datetime.timedelta(days=30),
                defaults={"amount": 500000, "payment_status": "unpaid"},
            )
            self.stdout.write(self.style.SUCCESS(f"عضو نمونه {first_name} {last_name} ({national_code}) ساخته شد."))

        self.stdout.write(self.style.SUCCESS("\n✅ داده‌ی نمونه با موفقیت ساخته شد."))
        self.stdout.write("رمز عبور همه‌ی کاربران = همان نام‌کاربری (شماره ملی) است.")