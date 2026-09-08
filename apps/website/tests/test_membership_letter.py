from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province


class MembershipLetterViewTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house = HealthHouse.objects.create(center=center, name="خانه الف")

    def test_letter_view_renders_with_data(self):
        response = self.client.get(reverse("website:membership_letter"), {
            "full_name": "حمزه نصیری", "national_code": "1234567890", "health_house": self.house.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "حمزه نصیری")
        self.assertContains(response, "1234567890")
        self.assertContains(response, "شبکه ساری")

    def test_letter_view_handles_missing_params_gracefully(self):
        response = self.client.get(reverse("website:membership_letter"))
        self.assertEqual(response.status_code, 200)


class MembershipApplicationFileUploadTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house = HealthHouse.objects.create(center=center, name="خانه الف")

    def _pdf(self, name):
        return SimpleUploadedFile(name, b"%PDF-1.4 fake", content_type="application/pdf")

    def test_application_succeeds_with_both_files(self):
        from apps.website.models import MembershipApplication

        response = self.client.post(reverse("website:membership_application"), {
            "first_name": "تست",
            "last_name": "فایل موفق",
            "national_code": "1112223336",
            "mobile_number": "09120000000",
            "province": self.house.center.network.county.province_id,
            "county": self.house.center.network.county_id,
            "network": self.house.center.network_id,
            "center": self.house.center_id,
            "health_house": self.house.id,
            "accepted_terms": "on",
            "legal_decree_file": self._pdf("decree.pdf"),
            "network_letter_file": self._pdf("letter.pdf"),
        })
        if response.status_code == 200:
            print("DEBUG form errors:", response.context["form"].errors)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(MembershipApplication.objects.filter(national_code="1112223336").exists())
