import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.committees.authorization import can_manage_committee
from apps.committees.choices import CommitteeStatus
from apps.committees.models import Committee, CommitteeMembership
from apps.committees.services import (
    activate_committee,
    add_committee_member,
    archive_committee,
    end_committee,
    remove_committee_member,
    suspend_committee,
)
from apps.organization.models import County, Province

User = get_user_model()


class CommitteeLifecycleTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        self.sari_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)

        self.committee = Committee.objects.create(name="کمیته آموزش", scope=self.sari_scope)

        self.manager = User.objects.create_user(username="committee_manager1", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(
            Permission.objects.get(code="committee.create"),
            Permission.objects.get(code="committee.update"),
            Permission.objects.get(code="committee.delete"),
            Permission.objects.get(code="committee.manage_members"),
            Permission.objects.get(code="committee.view"),
        )
        RoleAssignment.objects.create(
            user=self.manager, role=role, access_scope=self.sari_scope, start_date=datetime.date.today(),
        )

    def test_activate_committee(self):
        self.assertEqual(self.committee.status, CommitteeStatus.DRAFT)
        activate_committee(committee=self.committee, actor=self.manager)
        self.committee.refresh_from_db()
        self.assertEqual(self.committee.status, CommitteeStatus.ACTIVE)
        self.assertTrue(self.committee.is_active)

    def test_suspend_requires_reason(self):
        activate_committee(committee=self.committee, actor=self.manager)
        with self.assertRaises(ValidationError):
            suspend_committee(committee=self.committee, actor=self.manager, reason="")

    def test_full_lifecycle_to_archive(self):
        activate_committee(committee=self.committee, actor=self.manager)
        suspend_committee(committee=self.committee, actor=self.manager, reason="بازبینی")
        end_committee(committee=self.committee, actor=self.manager)
        archive_committee(committee=self.committee, actor=self.manager)
        self.committee.refresh_from_db()
        self.assertEqual(self.committee.status, CommitteeStatus.ARCHIVED)

    def test_invalid_transition_archived_to_active_blocked(self):
        self.committee.status = CommitteeStatus.ARCHIVED
        self.committee.save()
        with self.assertRaises(ValidationError):
            activate_committee(committee=self.committee, actor=self.manager)

    def test_unauthorized_user_cannot_activate(self):
        stranger = User.objects.create_user(username="committee_stranger", password="pass12345")
        with self.assertRaises(PermissionDenied):
            activate_committee(committee=self.committee, actor=stranger)


class CommitteeMembershipTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        self.committee = Committee.objects.create(name="کمیته سلامت", scope=scope)

        self.manager = User.objects.create_user(username="committee_member_manager", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="committee.manage_members"))
        RoleAssignment.objects.create(
            user=self.manager, role=role, access_scope=scope, start_date=datetime.date.today(),
        )

        self.target_user = User.objects.create_user(username="committee_target_user", password="pass12345")

    def test_add_member(self):
        membership = add_committee_member(
            committee=self.committee, user=self.target_user, added_by=self.manager,
            start_date=datetime.date.today(),
        )
        self.assertTrue(membership.is_active)

    def test_self_add_blocked(self):
        with self.assertRaises(PermissionDenied):
            add_committee_member(
                committee=self.committee, user=self.manager, added_by=self.manager,
                start_date=datetime.date.today(),
            )

    def test_remove_member_preserves_history(self):
        membership = CommitteeMembership.objects.create(
            committee=self.committee, user=self.target_user, start_date=datetime.date(2020, 1, 1),
        )
        remove_committee_member(membership=membership, removed_by=self.manager, end_date=datetime.date.today())
        membership.refresh_from_db()
        self.assertFalse(membership.is_active)
        self.assertTrue(CommitteeMembership.objects.filter(pk=membership.pk).exists())

    def test_user_can_be_member_of_multiple_committees(self):
        committee2 = Committee.objects.create(name="کمیته دوم")
        CommitteeMembership.objects.create(
            committee=self.committee, user=self.target_user, start_date=datetime.date.today(),
        )
        CommitteeMembership.objects.create(
            committee=committee2, user=self.target_user, start_date=datetime.date.today(),
        )
        self.assertEqual(
            CommitteeMembership.objects.filter(user=self.target_user, is_active=True).count(), 2
        )


class CommitteeChairViaRoleAssignmentTests(TestCase):
    """طبق تصمیم معماری: سمت‌های Chair/Secretary از RoleAssignment می‌آیند، نه فیلد مستقیم."""

    def setUp(self):
        self.committee = Committee.objects.create(name="کمیته ریاست")
        self.committee_scope = AccessScope.objects.create(
            scope_type=AccessScopeType.COMMITTEE, committee=self.committee
        )
        self.chair_user = User.objects.create_user(username="committee_chair_user", password="pass12345")

    def test_chair_assignment_scoped_to_specific_committee(self):
        chair_role = Role.objects.get(code="COMMITTEE_MANAGER")
        assignment = RoleAssignment.objects.create(
            user=self.chair_user, role=chair_role, access_scope=self.committee_scope,
            start_date=datetime.date.today(),
        )
        self.assertEqual(assignment.access_scope.committee, self.committee)

    def test_secretary_role_exists_and_assignable(self):
        secretary_role = Role.objects.get(code="COMMITTEE_SECRETARY")
        assignment = RoleAssignment.objects.create(
            user=self.chair_user, role=secretary_role, access_scope=self.committee_scope,
            start_date=datetime.date.today(),
        )
        self.assertEqual(assignment.role.code, "COMMITTEE_SECRETARY")

    def test_user_can_hold_multiple_committee_roles(self):
        """User A: Committee X = Chair, Committee Y = Member, Committee Z = Secretary"""
        committee_y = Committee.objects.create(name="کمیته Y")
        committee_z = Committee.objects.create(name="کمیته Z")
        scope_y = AccessScope.objects.create(scope_type=AccessScopeType.COMMITTEE, committee=committee_y)
        scope_z = AccessScope.objects.create(scope_type=AccessScopeType.COMMITTEE, committee=committee_z)

        CommitteeMembership.objects.create(
            committee=committee_y, user=self.chair_user, start_date=datetime.date.today()
        )
        RoleAssignment.objects.create(
            user=self.chair_user, role=Role.objects.get(code="COMMITTEE_MANAGER"),
            access_scope=self.committee_scope, start_date=datetime.date.today(),
        )
        RoleAssignment.objects.create(
            user=self.chair_user, role=Role.objects.get(code="COMMITTEE_SECRETARY"),
            access_scope=scope_z, start_date=datetime.date.today(),
        )

        roles = RoleAssignment.objects.for_user(self.chair_user).active()
        self.assertEqual(roles.count(), 2)


class CommitteeScopeGeographicContainmentTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        self.babol = County.objects.create(province=province, name="بابل")

        self.sari_committee_scope = AccessScope.objects.create(
            scope_type=AccessScopeType.COUNTY, county=self.sari
        )
        self.committee = Committee.objects.create(name="کمیته ساری", scope=self.sari_committee_scope)

        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="committee.view"))

        self.sari_manager = User.objects.create_user(username="geo_sari_manager", password="pass12345")
        sari_role_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        RoleAssignment.objects.create(
            user=self.sari_manager, role=role, access_scope=sari_role_scope, start_date=datetime.date.today(),
        )

        self.babol_manager = User.objects.create_user(username="geo_babol_manager", password="pass12345")
        babol_role_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.babol)
        RoleAssignment.objects.create(
            user=self.babol_manager, role=role, access_scope=babol_role_scope, start_date=datetime.date.today(),
        )

    def test_manager_of_same_county_can_view(self):
        self.assertTrue(can_manage_committee(self.sari_manager, self.committee, "committee.view"))

    def test_manager_of_different_county_cannot_view(self):
        """Scope Escape Prevention (بخش ۲۵ سند)"""
        self.assertFalse(can_manage_committee(self.babol_manager, self.committee, "committee.view"))


class CommitteeIDORTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        babol = County.objects.create(province=province, name="بابل")

        self.sari_committee = Committee.objects.create(
            name="کمیته ساری IDOR", scope=AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        )
        self.babol_committee = Committee.objects.create(
            name="کمیته بابل IDOR", scope=AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=babol)
        )

        self.viewer = User.objects.create_user(username="idor_committee_viewer", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="committee.view"))
        viewer_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        RoleAssignment.objects.create(
            user=self.viewer, role=role, access_scope=viewer_scope, start_date=datetime.date.today(),
        )

    def test_can_view_in_scope_committee(self):
        self.client.login(username="idor_committee_viewer", password="pass12345")
        response = self.client.get(reverse("committees_mgmt:detail", kwargs={"pk": self.sari_committee.pk}))
        self.assertEqual(response.status_code, 200)

    def test_idor_cannot_view_out_of_scope_committee(self):
        self.client.login(username="idor_committee_viewer", password="pass12345")
        response = self.client.get(reverse("committees_mgmt:detail", kwargs={"pk": self.babol_committee.pk}))
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_access_management_list(self):
        response = self.client.get(reverse("committees_mgmt:list"))
        self.assertEqual(response.status_code, 302)


class CommitteePublicVisibilityTests(TestCase):
    def test_private_committee_not_in_public_selector(self):
        from apps.committees.selectors import public_committees

        Committee.objects.create(
            name="کمیته خصوصی جدید", status=CommitteeStatus.ACTIVE, is_active=True, is_public_visible=False,
        )
        self.assertFalse(public_committees().filter(name="کمیته خصوصی جدید").exists())

    def test_public_active_committee_in_public_selector(self):
        from apps.committees.selectors import public_committees

        Committee.objects.create(
            name="کمیته عمومی جدید", status=CommitteeStatus.ACTIVE, is_active=True, is_public_visible=True,
        )
        self.assertTrue(public_committees().filter(name="کمیته عمومی جدید").exists())

    def test_draft_committee_not_public_even_if_visible_flag_true(self):
        from apps.committees.selectors import public_committees

        Committee.objects.create(
            name="کمیته پیش‌نویس عمومی", status=CommitteeStatus.DRAFT, is_public_visible=True,
        )
        self.assertFalse(public_committees().filter(name="کمیته پیش‌نویس عمومی").exists())