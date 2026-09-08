import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.employment import selectors
from apps.employment.models import EmploymentAssignment
from apps.employment.services import create_employment_assignment, end_employment_assignment
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

User = get_user_model()


class EmploymentManagementServicesTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        babol = County.objects.create(province=province, name="بابل")

        sari_network = HealthNetwork.objects.create(county=self.sari, name="شبکه ساری")
        sari_center = HealthCenter.objects.create(network=sari_network, name="مرکز ساری یک")
        self.sari_house = HealthHouse.objects.create(center=sari_center, name="خانه ساری الف")

        babol_network = HealthNetwork.objects.create(county=babol, name="شبکه بابل")
        babol_center = HealthCenter.objects.create(network=babol_network, name="مرکز بابل یک")
        self.babol_house = HealthHouse.objects.create(center=babol_center, name="خانه بابل الف")

        self.behvarz = User.objects.create_user(username="behvarz_mgmt", password="pass12345")

        self.manager = User.objects.create_user(username="sari_manager", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(
            Permission.objects.get(code="employment.create"),
            Permission.objects.get(code="employment.view"),
            Permission.objects.get(code="employment.update"),
        )
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        RoleAssignment.objects.create(
            user=self.manager, role=role, access_scope=scope, start_date=datetime.date.today(),
        )

    def test_manager_can_create_assignment_in_scope(self):
        assignment = create_employment_assignment(
            created_by=self.manager, user=self.behvarz, health_house=self.sari_house,
            employment_type="behvarz", start_date=datetime.date.today(),
        )
        self.assertTrue(assignment.pk)

    def test_user_without_permission_cannot_create_assignment(self):
        stranger = User.objects.create_user(username="mgmt_stranger", password="pass12345")
        with self.assertRaises(PermissionDenied):
            create_employment_assignment(
                created_by=stranger, user=self.behvarz, health_house=self.sari_house,
                employment_type="behvarz", start_date=datetime.date.today(),
            )

    def test_manager_can_end_assignment_in_scope(self):
        assignment = EmploymentAssignment.objects.create(
            user=self.behvarz, health_house=self.sari_house, start_date=datetime.date(2020, 1, 1),
        )
        end_employment_assignment(
            assignment=assignment, ended_by=self.manager, end_date=datetime.date.today(),
        )
        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)

    def test_manager_cannot_end_assignment_outside_scope(self):
        assignment = EmploymentAssignment.objects.create(
            user=self.behvarz, health_house=self.babol_house, start_date=datetime.date(2020, 1, 1),
        )
        with self.assertRaises(PermissionDenied):
            end_employment_assignment(
                assignment=assignment, ended_by=self.manager, end_date=datetime.date.today(),
            )

    def test_multiple_active_assignments_across_centers(self):
        """طبق بخش ۲.۲/۲۷.۳ سند: بهورز می‌تواند هم‌زمان در دو مرکز مختلف باشد."""
        EmploymentAssignment.objects.create(
            user=self.behvarz, health_house=self.sari_house, start_date=datetime.date.today(), is_primary=True,
        )
        EmploymentAssignment.objects.create(
            user=self.behvarz, health_house=self.babol_house, start_date=datetime.date.today(), is_primary=False,
        )
        active = EmploymentAssignment.objects.for_user(self.behvarz).active()
        self.assertEqual(active.count(), 2)
        centers = {a.health_house.center_id for a in active}
        self.assertEqual(len(centers), 2)

    def test_historical_assignment_preserved(self):
        """1398-1401 → House A, 1401-1404 → House B, 1404-Current → House C"""
        old1 = EmploymentAssignment.objects.create(
            user=self.behvarz, health_house=self.sari_house,
            start_date=datetime.date(2019, 1, 1), end_date=datetime.date(2022, 1, 1), is_active=False,
        )
        old2 = EmploymentAssignment.objects.create(
            user=self.behvarz, health_house=self.babol_house,
            start_date=datetime.date(2022, 1, 1), end_date=datetime.date(2025, 1, 1), is_active=False,
        )
        current = EmploymentAssignment.objects.create(
            user=self.behvarz, health_house=self.sari_house,
            start_date=datetime.date(2025, 1, 1), is_active=True, is_primary=True,
        )

        all_records = EmploymentAssignment.objects.for_user(self.behvarz)
        self.assertEqual(all_records.count(), 3)
        self.assertIn(old1, all_records)
        self.assertIn(old2, all_records)
        self.assertEqual(EmploymentAssignment.objects.for_user(self.behvarz).active().get(), current)


class EmploymentSelectorTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        self.center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house = HealthHouse.objects.create(center=self.center, name="خانه الف")
        self.county = county
        self.network = network

        self.user1 = User.objects.create_user(username="selector_u1", password="pass12345")
        self.user2 = User.objects.create_user(username="selector_u2", password="pass12345")

        EmploymentAssignment.objects.create(
            user=self.user1, health_house=self.house, start_date=datetime.date.today(), is_primary=True,
        )
        EmploymentAssignment.objects.create(
            user=self.user1, health_house=self.house, start_date=datetime.date(2020, 1, 1),
            end_date=datetime.date(2023, 1, 1), is_active=False,
        )

    def test_employees_by_health_house(self):
        self.assertEqual(selectors.employees_by_health_house(self.house).count(), 1)

    def test_employees_by_center(self):
        self.assertEqual(selectors.employees_by_center(self.center).count(), 1)

    def test_employees_by_network(self):
        self.assertEqual(selectors.employees_by_network(self.network).count(), 1)

    def test_employees_by_county(self):
        self.assertEqual(selectors.employees_by_county(self.county).count(), 1)

    def test_historical_employees_excludes_active(self):
        historical = selectors.historical_employees()
        self.assertEqual(historical.filter(user=self.user1).count(), 1)


class EmploymentManagementViewsIDORTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        babol = County.objects.create(province=province, name="بابل")

        sari_network = HealthNetwork.objects.create(county=self.sari, name="شبکه ساری")
        sari_center = HealthCenter.objects.create(network=sari_network, name="مرکز ساری یک")
        self.sari_house = HealthHouse.objects.create(center=sari_center, name="خانه ساری الف")

        babol_network = HealthNetwork.objects.create(county=babol, name="شبکه بابل")
        babol_center = HealthCenter.objects.create(network=babol_network, name="مرکز بابل یک")
        self.babol_house = HealthHouse.objects.create(center=babol_center, name="خانه بابل الف")

        behvarz_sari = User.objects.create_user(username="behvarz_sari_v", password="pass12345")
        behvarz_babol = User.objects.create_user(username="behvarz_babol_v", password="pass12345")

        self.sari_assignment = EmploymentAssignment.objects.create(
            user=behvarz_sari, health_house=self.sari_house, start_date=datetime.date.today(),
        )
        self.babol_assignment = EmploymentAssignment.objects.create(
            user=behvarz_babol, health_house=self.babol_house, start_date=datetime.date.today(),
        )

        self.manager = User.objects.create_user(username="sari_manager_v", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="employment.view"))
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        RoleAssignment.objects.create(
            user=self.manager, role=role, access_scope=scope, start_date=datetime.date.today(),
        )

    def test_manager_can_view_in_scope_assignment(self):
        self.client.login(username="sari_manager_v", password="pass12345")
        response = self.client.get(reverse("employment:detail", kwargs={"pk": self.sari_assignment.pk}))
        self.assertEqual(response.status_code, 200)

    def test_manager_cannot_view_out_of_scope_assignment_via_url_manipulation(self):
        """IDOR Protection — تغییر pk در URL نباید دسترسی خارج از Scope بدهد."""
        self.client.login(username="sari_manager_v", password="pass12345")
        response = self.client.get(reverse("employment:detail", kwargs={"pk": self.babol_assignment.pk}))
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_access_management_list(self):
        response = self.client.get(reverse("employment:list"))
        self.assertEqual(response.status_code, 302)

    def test_user_without_permission_gets_403_on_list(self):
        stranger = User.objects.create_user(username="mgmt_view_stranger", password="pass12345")
        self.client.login(username="mgmt_view_stranger", password="pass12345")
        response = self.client.get(reverse("employment:list"))
        self.assertEqual(response.status_code, 403)