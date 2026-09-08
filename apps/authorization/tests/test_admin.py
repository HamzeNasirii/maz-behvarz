import datetime

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.employment.models import EmploymentAssignment
from apps.members.admin import MemberAdmin
from apps.members.models import Member
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

User = get_user_model()


class MemberAdminAuthorizationTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        babol = County.objects.create(province=province, name="بابل")

        sari_network = HealthNetwork.objects.create(county=self.sari, name="شبکه ساری")
        sari_center = HealthCenter.objects.create(network=sari_network, name="مرکز ساری یک")
        sari_house = HealthHouse.objects.create(center=sari_center, name="خانه ساری الف")

        babol_network = HealthNetwork.objects.create(county=babol, name="شبکه بابل")
        babol_center = HealthCenter.objects.create(network=babol_network, name="مرکز بابل یک")
        babol_house = HealthHouse.objects.create(center=babol_center, name="خانه بابل الف")

        self.viewer = User.objects.create_user(username="admin_viewer", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="member.view"))
        sari_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        RoleAssignment.objects.create(
            user=self.viewer, role=role, access_scope=sari_scope,
            start_date=datetime.date.today(),
        )

        sari_user = User.objects.create_user(username="sari_admin_test", password="pass12345")
        self.sari_member = Member.objects.create(user=sari_user)
        EmploymentAssignment.objects.create(
            user=sari_user, health_house=sari_house,
            start_date=datetime.date.today(), is_primary=True,
        )

        babol_user = User.objects.create_user(username="babol_admin_test", password="pass12345")
        self.babol_member = Member.objects.create(user=babol_user)
        EmploymentAssignment.objects.create(
            user=babol_user, health_house=babol_house,
            start_date=datetime.date.today(), is_primary=True,
        )

        self.admin = MemberAdmin(Member, AdminSite())
        self.factory = RequestFactory()

    def _request_for(self, user):
        request = self.factory.get("/admin/members/member/")
        request.user = user
        return request

    def test_admin_queryset_scoped_to_user_access(self):
        request = self._request_for(self.viewer)
        qs = self.admin.get_queryset(request)
        self.assertIn(self.sari_member, qs)
        self.assertNotIn(self.babol_member, qs)

    def test_admin_view_permission_denied_for_out_of_scope_object(self):
        request = self._request_for(self.viewer)
        self.assertTrue(self.admin.has_view_permission(request, self.sari_member))
        self.assertFalse(self.admin.has_view_permission(request, self.babol_member))
