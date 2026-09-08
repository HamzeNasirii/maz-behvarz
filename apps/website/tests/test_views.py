from django.test import TestCase
from django.urls import reverse

from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

from ..models import MembershipApplication


class WebsiteViewsTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house = HealthHouse.objects.create(center=center, name="خانه الف")
        self.province = province
        self.county = county
        self.network = network
        self.center = center

    def test_home_page_loads(self):
        response = self.client.get(reverse("website:home"))
        self.assertEqual(response.status_code, 200)

    def test_membership_application_form_creates_record(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = self.client.post(
            reverse("website:membership_application"),
            {
                "first_name": "حمزه",
                "last_name": "نصیری",
                "national_code": "1234567890",
                "mobile_number": "09120000000",
                "province": self.province.id,
                "county": self.county.id,
                "network": self.network.id,
                "center": self.center.id,
                "health_house": self.house.id,
                "accepted_terms": "on",
                "legal_decree_file": SimpleUploadedFile("decree.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
                "network_letter_file": SimpleUploadedFile("letter.pdf", b"%PDF-1.4 fake",
                                                          content_type="application/pdf"),
            },
        )
        self.assertEqual(response.status_code, 302)
        application = MembershipApplication.objects.get(national_code="1234567890")
        self.assertEqual(application.health_house, self.house)
        self.assertTrue(application.accepted_terms)

    def test_application_rejected_without_accepting_terms(self):
        response = self.client.post(
            reverse("website:membership_application"),
            {
                "full_name": "حمزه نصیری",
                "national_code": "9876543210",
                "mobile_number": "09120000000",
                "province": self.province.id,
                "county": self.county.id,
                "network": self.network.id,
                "center": self.center.id,
                "health_house": self.house.id,
            },
        )
        self.assertEqual(response.status_code, 200)  # فرم دوباره با خطا نمایش داده می‌شود
        self.assertFalse(MembershipApplication.objects.filter(national_code="9876543210").exists())


class MembershipApplicationValidationTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house = HealthHouse.objects.create(center=center, name="خانه الف")
        self.province, self.county, self.network, self.center = province, county, network, center

    def _valid_payload(self, **overrides):
        payload = {
            "full_name": "تست اعتبارسنجی",
            "national_code": "1234567890",
            "mobile_number": "09121234567",
            "province": self.province.id,
            "county": self.county.id,
            "network": self.network.id,
            "center": self.center.id,
            "health_house": self.house.id,
            "accepted_terms": "on",
        }
        payload.update(overrides)
        return payload

    def test_invalid_national_code_rejected(self):
        response = self.client.post(
            reverse("website:membership_application"),
            self._valid_payload(national_code="12345"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MembershipApplication.objects.filter(national_code="12345").exists())

    def test_invalid_mobile_number_rejected(self):
        response = self.client.post(
            reverse("website:membership_application"),
            self._valid_payload(mobile_number="123456"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MembershipApplication.objects.filter(mobile_number="123456").exists())