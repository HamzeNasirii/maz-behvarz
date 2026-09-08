from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.organization.models import (
    Province,
    County,
    HealthNetwork,
    HealthCenter,
    HealthHouse,
)


class OrganizationHierarchyTests(TestCase):
    def setUp(self):
        self.province = Province.objects.create(name="مازندران", code="MAZ")
        self.county = County.objects.create(province=self.province, name="ساری", code="SAR")
        self.network = HealthNetwork.objects.create(county=self.county, name="شبکه ساری")
        self.center = HealthCenter.objects.create(network=self.network, name="مرکز شماره یک")
        self.house = HealthHouse.objects.create(center=self.center, name="خانه بهداشت الف")

    def test_province_creation(self):
        self.assertEqual(Province.objects.count(), 1)

    def test_county_belongs_to_province(self):
        self.assertEqual(self.county.province, self.province)

    def test_network_belongs_to_county(self):
        self.assertEqual(self.network.county, self.county)

    def test_center_belongs_to_network(self):
        self.assertEqual(self.center.network, self.network)

    def test_house_belongs_to_center(self):
        self.assertEqual(self.house.center, self.center)

    def test_house_can_reach_province_through_relationships(self):
        self.assertEqual(self.house.province, self.province)

    def test_duplicate_county_name_within_same_province_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                County.objects.create(province=self.province, name="ساری")

    def test_duplicate_network_name_within_same_county_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                HealthNetwork.objects.create(county=self.county, name="شبکه ساری")

    def test_duplicate_center_name_within_same_network_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                HealthCenter.objects.create(network=self.network, name="مرکز شماره یک")

    def test_duplicate_house_name_within_same_center_is_rejected(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                HealthHouse.objects.create(center=self.center, name="خانه بهداشت الف")