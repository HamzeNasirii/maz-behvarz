import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.authorization.services import Authorization
from apps.members.models import Member
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

User = get_user_model()


class AuthorizationEdgeCaseTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house = HealthHouse.objects.create(center=center, name="خانه الف")

        self.user = User.objects.create_user(username="edge_user", password="pass12345")
        member_user = User.objects.create_user(username="edge_member_user", password="pass12345")
        self.member = Member.objects.create(user=member_user)

        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="member.view"))
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        RoleAssignment.objects.create(
            user=self.user, role=role, access_scope=scope, start_date=datetime.date.today(),
        )

    def test_inactive_user_cannot_use_permission_even_with_valid_role(self):
        self.user.is_active = False
        self.user.save()
        self.assertFalse(Authorization.has_permission_code(self.user, "member.view"))

    def test_expired_role_assignment_does_not_grant_permission(self):
        RoleAssignment.objects.filter(user=self.user).update(
            start_date=datetime.date.today() - datetime.timedelta(days=10),
            end_date=datetime.date.today() - datetime.timedelta(days=1),
            is_active=False,
        )
        self.assertFalse(Authorization.has_permission_code(self.user, "member.view"))

    def test_future_role_assignment_does_not_grant_permission_yet(self):
        RoleAssignment.objects.filter(user=self.user).update(
            start_date=datetime.date.today() + datetime.timedelta(days=10)
        )
        self.assertFalse(Authorization.has_permission_code(self.user, "member.view"))

    def test_superuser_bypasses_scope_restrictions(self):
        superuser = User.objects.create_superuser(
            username="edge_superuser", password="pass12345", email="s@s.com"
        )
        self.assertTrue(Authorization.can(superuser, "member.view", self.member))