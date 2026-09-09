import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.members.choices import MembershipStatus
from apps.members.models import Member, MembershipStatusHistory
from apps.members.services import (
    activate_membership,
    approve_membership,
    cancel_membership,
    expire_membership,
    reinstate_membership,
    reject_membership,
    review_membership,
    submit_membership,
    suspend_membership,
)
from apps.organization.models import County, Province

User = get_user_model()


class MembershipLifecycleTests(TestCase):
    def setUp(self):
        self.applicant = User.objects.create_user(username="applicant1", password="pass12345")
        self.member = Member.objects.create(user=self.applicant)

        self.manager = User.objects.create_user(username="membership_manager", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(
            Permission.objects.get(code="membership.review"),
            Permission.objects.get(code="membership.approve"),
            Permission.objects.get(code="membership.suspend"),
            Permission.objects.get(code="membership.reinstate"),
            Permission.objects.get(code="membership.expire"),
            Permission.objects.get(code="membership.cancel"),
        )
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        RoleAssignment.objects.create(
            user=self.manager, role=role, access_scope=scope, start_date=datetime.date.today(),
        )

    def test_full_happy_path_lifecycle(self):
        submit_membership(member=self.member, actor=self.applicant)
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, MembershipStatus.SUBMITTED)

        review_membership(member=self.member, actor=self.manager)
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, MembershipStatus.UNDER_REVIEW)

        approve_membership(member=self.member, actor=self.manager)
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, MembershipStatus.APPROVED)

        activate_membership(member=self.member, actor=self.manager)
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, MembershipStatus.ACTIVE)
        self.assertEqual(self.member.membership_periods.count(), 1)

    def test_rejection_path(self):
        submit_membership(member=self.member, actor=self.applicant)
        review_membership(member=self.member, actor=self.manager)
        reject_membership(member=self.member, actor=self.manager, reason="مدارک ناقص")
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, MembershipStatus.REJECTED)

    def test_rejection_requires_reason(self):
        submit_membership(member=self.member, actor=self.applicant)
        review_membership(member=self.member, actor=self.manager)
        with self.assertRaises(ValidationError):
            reject_membership(member=self.member, actor=self.manager, reason="")

    def test_suspend_and_reinstate(self):
        self.member.status = MembershipStatus.ACTIVE
        self.member.save()
        suspend_membership(member=self.member, actor=self.manager, reason="عدم پرداخت")
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, MembershipStatus.SUSPENDED)

        reinstate_membership(member=self.member, actor=self.manager)
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, MembershipStatus.ACTIVE)

    def test_expire_then_renew_via_reinstate(self):
        self.member.status = MembershipStatus.ACTIVE
        self.member.save()
        expire_membership(member=self.member, actor=self.manager)
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, MembershipStatus.EXPIRED)

        reinstate_membership(member=self.member, actor=self.manager, reason="تمدید")
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, MembershipStatus.ACTIVE)

    def test_cancel_requires_reason(self):
        self.member.status = MembershipStatus.ACTIVE
        self.member.save()
        with self.assertRaises(ValidationError):
            cancel_membership(member=self.member, actor=self.manager, reason="")

    def test_cancel_is_final(self):
        self.member.status = MembershipStatus.ACTIVE
        self.member.save()
        cancel_membership(member=self.member, actor=self.manager, reason="درخواست شخصی")
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, MembershipStatus.CANCELLED)

    def test_invalid_transition_cancelled_to_active_blocked(self):
        self.member.status = MembershipStatus.CANCELLED
        self.member.save()
        with self.assertRaises(ValidationError):
            activate_membership(member=self.member, actor=self.manager)

    def test_only_owner_can_submit(self):
        stranger = User.objects.create_user(username="submit_stranger", password="pass12345")
        with self.assertRaises(PermissionDenied):
            submit_membership(member=self.member, actor=stranger)

    def test_user_without_permission_cannot_approve(self):
        submit_membership(member=self.member, actor=self.applicant)
        review_membership(member=self.member, actor=self.manager)
        with self.assertRaises(PermissionDenied):
            approve_membership(member=self.member, actor=self.applicant)

    def test_history_recorded_with_actor_and_timestamp(self):
        submit_membership(member=self.member, actor=self.applicant)
        history = MembershipStatusHistory.objects.filter(member=self.member).first()
        self.assertEqual(history.actor, self.applicant)
        self.assertIsNotNone(history.created_at)
        self.assertEqual(history.previous_status, MembershipStatus.DRAFT)
        self.assertEqual(history.new_status, MembershipStatus.SUBMITTED)


class MembershipScopeAndIDORTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        babol = County.objects.create(province=province, name="بابل")

        sari_user = User.objects.create_user(username="sari_membership_user", password="pass12345")
        self.sari_member = Member.objects.create(user=sari_user, status=MembershipStatus.SUBMITTED)

        babol_user = User.objects.create_user(username="babol_membership_user", password="pass12345")
        self.babol_member = Member.objects.create(user=babol_user, status=MembershipStatus.SUBMITTED)

        self.sari_manager = User.objects.create_user(username="sari_membership_manager", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="membership.review"))
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        RoleAssignment.objects.create(
            user=self.sari_manager, role=role, access_scope=scope, start_date=datetime.date.today(),
        )

        # این کاربر باید بتونه به‌عنوان behvarz در Sari محسوب بشه تا Scope درست کار کنه
        from apps.employment.models import EmploymentAssignment
        from apps.organization.models import HealthCenter, HealthHouse, HealthNetwork

        sari_network = HealthNetwork.objects.create(county=self.sari, name="شبکه ساری")
        sari_center = HealthCenter.objects.create(network=sari_network, name="مرکز ساری")
        sari_house = HealthHouse.objects.create(center=sari_center, name="خانه ساری")
        EmploymentAssignment.objects.create(
            user=sari_user, health_house=sari_house, start_date=datetime.date.today(), is_primary=True,
        )

        babol_network = HealthNetwork.objects.create(county=babol, name="شبکه بابل")
        babol_center = HealthCenter.objects.create(network=babol_network, name="مرکز بابل")
        babol_house = HealthHouse.objects.create(center=babol_center, name="خانه بابل")
        EmploymentAssignment.objects.create(
            user=babol_user, health_house=babol_house, start_date=datetime.date.today(), is_primary=True,
        )

    def test_manager_can_view_in_scope_membership(self):
        self.client.login(username="sari_membership_manager", password="pass12345")
        response = self.client.get(
            reverse("members_portal:membership_management_detail", kwargs={"pk": self.sari_member.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_manager_cannot_view_out_of_scope_membership_idor(self):
        self.client.login(username="sari_membership_manager", password="pass12345")
        response = self.client.get(
            reverse("members_portal:membership_management_detail", kwargs={"pk": self.babol_member.pk})
        )
        self.assertEqual(response.status_code, 403)

    def test_management_list_only_shows_in_scope(self):
        self.client.login(username="sari_membership_manager", password="pass12345")
        response = self.client.get(reverse("members_portal:membership_management_list"))
        self.assertContains(response, "sari_membership_user")
        self.assertNotContains(response, "babol_membership_user")