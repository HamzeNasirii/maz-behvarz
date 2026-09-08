import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.authorization.policies.employment import EmploymentAssignmentPolicy
from apps.authorization.services import Authorization
from apps.employment.models import EmploymentAssignment
from apps.members.models import Member
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

User = get_user_model()


class AuthorizationEngineTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")

        self.sari = County.objects.create(province=province, name="ساری")
        sari_network = HealthNetwork.objects.create(county=self.sari, name="شبکه ساری")
        sari_center = HealthCenter.objects.create(network=sari_network, name="مرکز ساری یک")
        self.sari_house = HealthHouse.objects.create(center=sari_center, name="خانه ساری الف")

        babol = County.objects.create(province=province, name="بابل")
        babol_network = HealthNetwork.objects.create(county=babol, name="شبکه بابل")
        babol_center = HealthCenter.objects.create(network=babol_network, name="مرکز بابل یک")
        self.babol_house = HealthHouse.objects.create(center=babol_center, name="خانه بابل الف")

        self.viewer = User.objects.create_user(username="viewer", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="member.view"))

        sari_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        RoleAssignment.objects.create(
            user=self.viewer, role=role, access_scope=sari_scope,
            start_date=datetime.date.today(),
        )

        self.sari_user = User.objects.create_user(username="sari_behvarz", password="pass12345")
        self.sari_member = Member.objects.create(user=self.sari_user)
        EmploymentAssignment.objects.create(
            user=self.sari_user, health_house=self.sari_house,
            start_date=datetime.date.today(), is_primary=True,
        )

        self.babol_user = User.objects.create_user(username="babol_behvarz", password="pass12345")
        self.babol_member = Member.objects.create(user=self.babol_user)
        EmploymentAssignment.objects.create(
            user=self.babol_user, health_house=self.babol_house,
            start_date=datetime.date.today(), is_primary=True,
        )

    def test_inactive_user_has_no_permission(self):
        self.viewer.is_active = False
        self.viewer.save()
        self.assertFalse(Authorization.has_permission_code(self.viewer, "member.view"))

    def test_user_without_role_has_no_permission(self):
        stranger = User.objects.create_user(username="stranger", password="pass12345")
        self.assertFalse(Authorization.has_permission_code(stranger, "member.view"))

    def test_can_view_member_within_scope(self):
        self.assertTrue(Authorization.can(self.viewer, "member.view", self.sari_member))

    def test_cannot_view_member_outside_scope(self):
        self.assertFalse(Authorization.can(self.viewer, "member.view", self.babol_member))

    def test_scope_queryset_filters_by_scope(self):
        scoped = Authorization.scope_queryset(self.viewer, Member.objects.all())
        self.assertIn(self.sari_member, scoped)
        self.assertNotIn(self.babol_member, scoped)

    def test_employment_assignment_can_never_be_deleted_by_policy(self):
        policy = EmploymentAssignmentPolicy()
        assignment = EmploymentAssignment.objects.for_user(self.sari_user).first()
        self.assertFalse(policy.can_delete(self.viewer, assignment))

