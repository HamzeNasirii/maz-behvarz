import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.board.choices import BoardPosition
from apps.board.models import BoardMembership
from apps.members.models import Member
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province
from apps.website.models import MembershipApplication

User = get_user_model()


class PendingManagementPagesAccessTests(TestCase):
    def setUp(self):
        self.chairman = User.objects.create_user(username="pmp_chairman", password="pass12345")
        BoardMembership.objects.create(
            user=self.chairman, position=BoardPosition.CHAIRMAN, start_date=timezone.localdate(),
        )
        self.ordinary_user = User.objects.create_user(username="pmp_ordinary", password="pass12345")

    def test_chairman_can_access_all_four_pages(self):
        self.client.login(username="pmp_chairman", password="pass12345")
        for url_name in ["applications", "members", "employment", "roles"]:
            response = self.client.get(reverse(f"pending_mgmt:{url_name}"))
            self.assertEqual(response.status_code, 200, f"{url_name} failed")

    def test_ordinary_user_denied_all_four_pages(self):
        self.client.login(username="pmp_ordinary", password="pass12345")
        for url_name in ["applications", "members", "employment", "roles"]:
            response = self.client.get(reverse(f"pending_mgmt:{url_name}"))
            self.assertEqual(response.status_code, 403, f"{url_name} should be denied")


class PendingMembershipApplicationApprovalTests(TestCase):
    def setUp(self):
        from apps.authorization.choices import AccessScopeType
        from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment

        self.chairman = User.objects.create_user(username="pmp_approver_chairman", password="pass12345")
        BoardMembership.objects.create(
            user=self.chairman, position=BoardPosition.CHAIRMAN, start_date=timezone.localdate(),
        )

        province = Province.objects.create(name="مازندران تست")
        county = County.objects.create(province=province, name="ساری تست")
        network = HealthNetwork.objects.create(county=county, name="شبکه تست")
        center = HealthCenter.objects.create(network=network, name="مرکز تست")
        self.house = HealthHouse.objects.create(center=center, name="خانه تست")

        # طبق تصمیم معماری جدید: دیگر هیچ Bypass عمومی برای هیئت‌مدیره
        # وجود ندارد — باید مثل هر کاربر دیگری، RoleAssignment واقعی
        # (با Permission لازم) داشته باشد.
        board_role = Role.objects.get(code="BOARD_MEMBER")
        board_role.permissions.add(Permission.objects.get(code="member.approve"))
        province_scope = AccessScope.objects.create(scope_type=AccessScopeType.PROVINCE, province=province)
        RoleAssignment.objects.create(
            user=self.chairman, role=board_role, access_scope=province_scope, start_date=timezone.localdate(),
        )

        self.application = MembershipApplication.objects.create(
            full_name="متقاضی تست", national_code="1234509876", mobile_number="09120000001",
            health_house=self.house, accepted_terms=True,
        )

    def test_chairman_can_approve_membership_application(self):
        self.client.login(username="pmp_approver_chairman", password="pass12345")
        response = self.client.post(reverse("pending_mgmt:applications"), {
            "item_id": self.application.pk, "action": "approve",
        })
        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "approved")
        self.assertTrue(Member.objects.filter(user__username=self.application.national_code).exists())

    def test_chairman_can_reject_membership_application_with_reason(self):
        self.client.login(username="pmp_approver_chairman", password="pass12345")
        response = self.client.post(reverse("pending_mgmt:applications"), {
            "item_id": self.application.pk, "action": "reject", "reason": "مدارک ناقص است.",
        })
        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "rejected")


class PendingRequestsBadgeTests(TestCase):
    def setUp(self):
        from apps.authorization.choices import AccessScopeType
        from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment

        self.chairman = User.objects.create_user(username="badge_chairman", password="pass12345")
        BoardMembership.objects.create(
            user=self.chairman, position=BoardPosition.CHAIRMAN, start_date=timezone.localdate(),
        )

        province = Province.objects.create(name="مازندران بج تست")
        county = County.objects.create(province=province, name="ساری بج تست")
        network = HealthNetwork.objects.create(county=county, name="شبکه بج تست")
        center = HealthCenter.objects.create(network=network, name="مرکز بج تست")
        self.house = HealthHouse.objects.create(center=center, name="خانه بج تست")

        # طبق تصمیم معماری جدید: دیگر هیچ Bypass عمومی برای هیئت‌مدیره
        # وجود ندارد — باید مثل هر کاربر دیگری، RoleAssignment واقعی
        # (با Permission لازم) داشته باشد تا Badge محاسبه شود.
        board_role = Role.objects.get(code="BOARD_MEMBER")
        board_role.permissions.add(Permission.objects.get(code="member.approve"))
        province_scope = AccessScope.objects.create(scope_type=AccessScopeType.PROVINCE, province=province)
        from apps.authorization.choices import ApprovalStatus

        RoleAssignment.objects.create(
            user=self.chairman, role=board_role, access_scope=province_scope, start_date=timezone.localdate(),
            approval_status=ApprovalStatus.APPROVED,
        )

    def test_badge_shows_count_when_pending_exists(self):
        MembershipApplication.objects.create(
            full_name="متقاضی بج", national_code="1112223339", mobile_number="09120000009",
            health_house=self.house, accepted_terms=True,
        )
        self.client.login(username="badge_chairman", password="pass12345")
        response = self.client.get(reverse("members_portal:dashboard"))
        self.assertContains(response, '<span class="badge badge-warning"')

    def test_badge_hidden_when_no_pending(self):
        self.client.login(username="badge_chairman", password="pass12345")
        response = self.client.get(reverse("members_portal:dashboard"))
        self.assertNotContains(response, '<span class="badge badge-warning"')

    def test_ordinary_user_does_not_trigger_pending_count_query(self):
        """کاربر عادی نباید حتی can_view_pending_dashboard در context داشته باشد."""
        ordinary = User.objects.create_user(username="badge_ordinary", password="pass12345")
        self.client.login(username="badge_ordinary", password="pass12345")
        response = self.client.get(reverse("members_portal:dashboard"))
        self.assertNotIn("pending_requests_count", response.context)
