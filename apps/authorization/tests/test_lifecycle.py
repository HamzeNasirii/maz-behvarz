import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.authorization.choices import AccessScopeType, RoleAssignmentStatus
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment, RoleAssignmentStatusHistory
from apps.authorization.role_lifecycle_services import (
    approve_role_assignment_lifecycle,
    assign_role,
    cancel_role_assignment,
    end_role_assignment,
    reactivate_role_assignment,
    reject_role_assignment_lifecycle,
    revoke_role_assignment,
    submit_role_assignment_for_approval,
    suspend_role_assignment,
)
from apps.authorization.services import Authorization
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

User = get_user_model()


class RoleLifecycleTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        babol = County.objects.create(province=province, name="بابل")

        sari_network = HealthNetwork.objects.create(county=self.sari, name="شبکه ساری")
        sari_center = HealthCenter.objects.create(network=sari_network, name="مرکز ساری")
        sari_house = HealthHouse.objects.create(center=sari_center, name="خانه ساری")

        babol_network = HealthNetwork.objects.create(county=babol, name="شبکه بابل")
        babol_center = HealthCenter.objects.create(network=babol_network, name="مرکز بابل")
        self.babol_house = HealthHouse.objects.create(center=babol_center, name="خانه بابل")

        self.behvarz = User.objects.create_user(username="role_target_user", password="pass12345")
        self.role = Role.objects.get(code="COUNTY_REPRESENTATIVE")
        self.sari_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        self.babol_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=babol)

        self.sari_admin = User.objects.create_user(username="sari_role_admin", password="pass12345")
        admin_role = Role.objects.get(code="BEHVARZ")
        admin_role.permissions.add(
            Permission.objects.get(code="role.assign"),
            Permission.objects.get(code="role.approve"),
            Permission.objects.get(code="role.revoke"),
            Permission.objects.get(code="role.view"),
        )
        RoleAssignment.objects.create(
            user=self.sari_admin, role=admin_role, access_scope=self.sari_scope, start_date=datetime.date.today(),
        )
        # سازمانی-یاب برای اینکه sari_admin بتونه Scope رو containment کنه
        EmploymentAssignment = __import__("apps.employment.models", fromlist=["EmploymentAssignment"]).EmploymentAssignment
        EmploymentAssignment.objects.create(
            user=self.sari_admin, health_house=sari_house, start_date=datetime.date.today(), is_primary=True,
        )

    def test_full_happy_path(self):
        assignment = assign_role(
            assigned_by=self.sari_admin, user=self.behvarz, role=self.role,
            access_scope=self.sari_scope, start_date=datetime.date.today(),
        )
        self.assertEqual(assignment.status, RoleAssignmentStatus.PROPOSED)
        self.assertFalse(assignment.is_active)

        submit_role_assignment_for_approval(assignment=assignment, actor=self.sari_admin)
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RoleAssignmentStatus.PENDING_APPROVAL)

        other_admin = User.objects.create_user(username="other_role_admin", password="pass12345")
        admin_role = Role.objects.get(code="BEHVARZ")
        RoleAssignment.objects.create(
            user=other_admin, role=admin_role, access_scope=self.sari_scope, start_date=datetime.date.today(),
        )
        approve_role_assignment_lifecycle(assignment=assignment, actor=other_admin)
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RoleAssignmentStatus.ACTIVE)
        self.assertTrue(assignment.is_active)

    def test_self_approval_blocked(self):
        assignment = assign_role(
            assigned_by=self.sari_admin, user=self.behvarz, role=self.role,
            access_scope=self.sari_scope, start_date=datetime.date.today(),
        )
        submit_role_assignment_for_approval(assignment=assignment, actor=self.sari_admin)
        with self.assertRaises(PermissionDenied):
            approve_role_assignment_lifecycle(assignment=assignment, actor=self.sari_admin)

    def test_self_role_assignment_blocked(self):
        """طبق بخش ۳۰ سند: کاربر نباید بتواند برای خودش نقش بسازد."""
        with self.assertRaises(PermissionDenied):
            assign_role(
                assigned_by=self.sari_admin, user=self.sari_admin, role=self.role,
                access_scope=self.sari_scope, start_date=datetime.date.today(),
            )

    def test_county_manager_cannot_assign_role_outside_own_scope(self):
        """طبق بخش ۱۶ سند: نماینده‌ی ساری نباید بتواند نقش در بابل بسازد."""
        with self.assertRaises(PermissionDenied):
            assign_role(
                assigned_by=self.sari_admin, user=self.behvarz, role=self.role,
                access_scope=self.babol_scope, start_date=datetime.date.today(),
            )

    def test_invalid_transition_ended_to_active_blocked(self):
        assignment = RoleAssignment.objects.create(
            user=self.behvarz, role=self.role, access_scope=self.sari_scope,
            start_date=datetime.date.today(), status=RoleAssignmentStatus.ENDED, is_active=False,
        )
        with self.assertRaises(ValidationError):
            approve_role_assignment_lifecycle(assignment=assignment, actor=self.sari_admin)

    def test_reject_requires_reason(self):
        assignment = assign_role(
            assigned_by=self.sari_admin, user=self.behvarz, role=self.role,
            access_scope=self.sari_scope, start_date=datetime.date.today(),
        )
        submit_role_assignment_for_approval(assignment=assignment, actor=self.sari_admin)
        with self.assertRaises(ValidationError):
            reject_role_assignment_lifecycle(assignment=assignment, actor=self.sari_admin, reason="")

    def test_suspend_and_reactivate(self):
        assignment = RoleAssignment.objects.create(
            user=self.behvarz, role=self.role, access_scope=self.sari_scope,
            start_date=datetime.date.today(), status=RoleAssignmentStatus.ACTIVE, is_active=True,
        )
        suspend_role_assignment(assignment=assignment, actor=self.sari_admin, reason="بررسی مجدد")
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RoleAssignmentStatus.SUSPENDED)
        self.assertFalse(assignment.is_active)

        reactivate_role_assignment(assignment=assignment, actor=self.sari_admin)
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, RoleAssignmentStatus.ACTIVE)
        self.assertTrue(assignment.is_active)

    def test_revoke_requires_reason(self):
        assignment = RoleAssignment.objects.create(
            user=self.behvarz, role=self.role, access_scope=self.sari_scope,
            start_date=datetime.date.today(), status=RoleAssignmentStatus.ACTIVE, is_active=True,
        )
        with self.assertRaises(ValidationError):
            revoke_role_assignment(assignment=assignment, actor=self.sari_admin, reason="")

    def test_multiple_roles_and_scopes_simultaneously(self):
        """بخش ۵/۶ سند: چند نقش هم‌زمان در Scopeهای مستقل معتبرند."""
        province_scope = AccessScope.objects.create(scope_type=AccessScopeType.PROVINCE, province=self.sari.province)
        board_role = Role.objects.get(code="BOARD_MEMBER")

        RoleAssignment.objects.create(
            user=self.behvarz, role=self.role, access_scope=self.sari_scope, start_date=datetime.date.today(),
        )
        RoleAssignment.objects.create(
            user=self.behvarz, role=board_role, access_scope=province_scope, start_date=datetime.date.today(),
        )
        active = RoleAssignment.objects.for_user(self.behvarz).active()
        self.assertEqual(active.count(), 2)

    def test_history_recorded_with_actor(self):
        assignment = assign_role(
            assigned_by=self.sari_admin, user=self.behvarz, role=self.role,
            access_scope=self.sari_scope, start_date=datetime.date.today(),
        )
        history = RoleAssignmentStatusHistory.objects.filter(role_assignment=assignment).first()
        self.assertEqual(history.actor, self.sari_admin)
        self.assertEqual(history.new_status, RoleAssignmentStatus.PROPOSED)


class RoleAssignmentIDORAndScopeTests(TestCase):
    def setUp(self):
        from apps.employment.models import EmploymentAssignment

        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        babol = County.objects.create(province=province, name="بابل")

        sari_network = HealthNetwork.objects.create(county=self.sari, name="شبکه ساری۲")
        sari_center = HealthCenter.objects.create(network=sari_network, name="مرکز ساری۲")
        sari_house = HealthHouse.objects.create(center=sari_center, name="خانه ساری۲")

        babol_network = HealthNetwork.objects.create(county=babol, name="شبکه بابل۲")
        babol_center = HealthCenter.objects.create(network=babol_network, name="مرکز بابل۲")
        babol_house = HealthHouse.objects.create(center=babol_center, name="خانه بابل۲")

        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="role.view"))

        self.sari_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        babol_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=babol)

        sari_target = User.objects.create_user(username="sari_role_target", password="pass12345")
        self.sari_assignment = RoleAssignment.objects.create(
            user=sari_target, role=role, access_scope=self.sari_scope, start_date=datetime.date.today(),
        )

        babol_target = User.objects.create_user(username="babol_role_target", password="pass12345")
        self.babol_assignment = RoleAssignment.objects.create(
            user=babol_target, role=role, access_scope=babol_scope, start_date=datetime.date.today(),
        )

        self.viewer = User.objects.create_user(username="sari_role_viewer", password="pass12345")
        RoleAssignment.objects.create(
            user=self.viewer, role=role, access_scope=self.sari_scope, start_date=datetime.date.today(),
        )
        EmploymentAssignment.objects.create(
            user=self.viewer, health_house=sari_house, start_date=datetime.date.today(), is_primary=True,
        )

    def test_manager_can_view_in_scope_assignment(self):
        self.client.login(username="sari_role_viewer", password="pass12345")
        response = self.client.get(reverse("roles:management_detail", kwargs={"pk": self.sari_assignment.pk}))
        self.assertEqual(response.status_code, 200)

    def test_idor_manager_cannot_view_out_of_scope_assignment(self):
        self.client.login(username="sari_role_viewer", password="pass12345")
        response = self.client.get(reverse("roles:management_detail", kwargs={"pk": self.babol_assignment.pk}))
        self.assertEqual(response.status_code, 403)

    def test_management_list_scope_aware(self):
        self.client.login(username="sari_role_viewer", password="pass12345")
        response = self.client.get(reverse("roles:management_list"))
        self.assertContains(response, "sari_role_target")
        self.assertNotContains(response, "babol_role_target")

    def test_unauthenticated_cannot_access_management_list(self):
        response = self.client.get(reverse("roles:management_list"))
        self.assertEqual(response.status_code, 302)


class TemporalRoleTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        self.scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        self.user = User.objects.create_user(username="temporal_role_user", password="pass12345")
        self.role = Role.objects.get(code="BEHVARZ")
        self.role.permissions.add(Permission.objects.get(code="member.view"))

    def test_future_role_grants_no_permission_yet(self):
        RoleAssignment.objects.create(
            user=self.user, role=self.role, access_scope=self.scope,
            start_date=datetime.date.today() + datetime.timedelta(days=10),
        )
        self.assertFalse(Authorization.has_permission_code(self.user, "member.view"))

    def test_expired_role_grants_no_permission(self):
        RoleAssignment.objects.create(
            user=self.user, role=self.role, access_scope=self.scope,
            start_date=datetime.date.today() - datetime.timedelta(days=100),
            end_date=datetime.date.today() - datetime.timedelta(days=1),
            is_active=False,
        )
        self.assertFalse(Authorization.has_permission_code(self.user, "member.view"))

    def test_active_role_grants_permission(self):
        RoleAssignment.objects.create(
            user=self.user, role=self.role, access_scope=self.scope,
            start_date=datetime.date.today() - datetime.timedelta(days=1),
        )
        self.assertTrue(Authorization.has_permission_code(self.user, "member.view"))