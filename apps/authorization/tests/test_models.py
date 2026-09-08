import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope
from apps.organization.models import Province, County, HealthNetwork, HealthCenter, HealthHouse

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import Permission, Role, AccessScope, RoleAssignment

User = get_user_model()


class PermissionAndRoleTests(TestCase):
    def test_permission_seeded(self):
        self.assertTrue(Permission.objects.filter(code="member.view").exists())

    def test_role_seeded(self):
        self.assertTrue(Role.objects.filter(code="BEHVARZ").exists())

    def test_permission_code_unique(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Permission.objects.create(code="member.view")


class RoleAssignmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="pass12345")
        self.behvarz = Role.objects.get(code="BEHVARZ")
        self.board = Role.objects.get(code="BOARD_MEMBER")

        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")

        self.county_scope = AccessScope.objects.create(
            scope_type=AccessScopeType.COUNTY, county=county
        )
        self.global_scope = AccessScope.objects.create(scope_type=AccessScopeType.GLOBAL)

    def test_user_can_have_multiple_roles_simultaneously(self):
        RoleAssignment.objects.create(
            user=self.user, role=self.behvarz, access_scope=self.county_scope,
            start_date=datetime.date.today(),
        )
        RoleAssignment.objects.create(
            user=self.user, role=self.board, access_scope=self.global_scope,
            start_date=datetime.date.today(),
        )
        self.assertEqual(
            RoleAssignment.objects.for_user(self.user).active().count(), 2
        )

    def test_role_assignment_requires_end_after_start(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RoleAssignment.objects.create(
                    user=self.user, role=self.behvarz, access_scope=self.county_scope,
                    start_date=datetime.date(2025, 1, 1),
                    end_date=datetime.date(2024, 1, 1),
                )



class HierarchicalAccessScopeTests(TestCase):
    def setUp(self):
        self.province = Province.objects.create(name="مازندران")

        self.sari = County.objects.create(province=self.province, name="ساری")
        self.sari_network = HealthNetwork.objects.create(county=self.sari, name="شبکه ساری")
        self.sari_center = HealthCenter.objects.create(network=self.sari_network, name="مرکز ساری یک")
        self.sari_house = HealthHouse.objects.create(center=self.sari_center, name="خانه ساری الف")

        self.babol = County.objects.create(province=self.province, name="بابل")
        self.babol_network = HealthNetwork.objects.create(county=self.babol, name="شبکه بابل")
        self.babol_center = HealthCenter.objects.create(network=self.babol_network, name="مرکز بابل یک")
        self.babol_house = HealthHouse.objects.create(center=self.babol_center, name="خانه بابل الف")

    def test_county_scope_contains_only_its_own_hierarchy(self):
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        self.assertTrue(scope.contains_health_house(self.sari_house))
        self.assertFalse(scope.contains_health_house(self.babol_house))

    def test_global_scope_contains_everything(self):
        scope = AccessScope.objects.create(scope_type=AccessScopeType.GLOBAL)
        self.assertTrue(scope.contains_health_house(self.sari_house))
        self.assertTrue(scope.contains_health_house(self.babol_house))

    def test_house_scope_contains_only_itself(self):
        scope = AccessScope.objects.create(scope_type=AccessScopeType.HOUSE, house=self.sari_house)
        self.assertTrue(scope.contains_health_house(self.sari_house))
        self.assertFalse(scope.contains_health_house(self.babol_house))

    def test_province_scope_requires_province_field(self):
        scope = AccessScope(scope_type=AccessScopeType.PROVINCE)
        with self.assertRaises(ValidationError):
            scope.full_clean()

    def test_county_scope_rejects_extra_fields(self):
        scope = AccessScope(
            scope_type=AccessScopeType.COUNTY, county=self.sari, network=self.sari_network
        )
        with self.assertRaises(ValidationError):
            scope.full_clean()