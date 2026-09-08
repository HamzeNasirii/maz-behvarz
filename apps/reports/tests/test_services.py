import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.employment.models import EmploymentAssignment
from apps.members.models import Member
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province
from apps.reports.services import (
    board_and_committee_statistics,
    county_coverage_statistics,
    employment_statistics,
    member_statistics,
)

User = get_user_model()


class ReportsServiceTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="reports_admin", password="pass12345", email="a@a.com"
        )

        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        house = HealthHouse.objects.create(center=center, name="خانه الف")

        user1 = User.objects.create_user(username="report_user1", password="pass12345")
        Member.objects.create(user=user1)
        EmploymentAssignment.objects.create(
            user=user1, health_house=house, start_date=datetime.date.today(), is_primary=True,
        )

    def test_member_statistics_for_superuser(self):
        stats = member_statistics(self.superuser)
        self.assertEqual(stats["total"], 1)

    def test_employment_statistics_groups_by_county(self):
        stats = employment_statistics(self.superuser)
        self.assertEqual(stats["total_active"], 1)
        self.assertIn("ساری", stats["by_county"])

    def test_board_and_committee_statistics_runs_without_error(self):
        stats = board_and_committee_statistics(self.superuser)
        self.assertIn("active_board_members", stats)

    def test_county_coverage_statistics(self):
        stats = county_coverage_statistics(self.superuser)
        self.assertEqual(stats["total_counties"], 1)
        self.assertEqual(stats["counties_with_active_members"], 1)