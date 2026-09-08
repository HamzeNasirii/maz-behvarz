from django.test import TestCase, override_settings
from django.urls import reverse

from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province
from django.core.cache import cache

@override_settings(RATELIMIT_ENABLE=True)
class MembershipApplicationRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        super().setUp()
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house = HealthHouse.objects.create(center=center, name="خانه الف")

    def _payload(self, code):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return {
            "first_name": "تست",
            "last_name": "ریت لیمیت",
            "national_code": code,
            "mobile_number": "09121112233",
            "province": self.house.center.network.county.province_id,
            "county": self.house.center.network.county_id,
            "network": self.house.center.network_id,
            "center": self.house.center_id,
            "health_house": self.house.id,
            "accepted_terms": "on",
            "legal_decree_file": SimpleUploadedFile("decree.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            "network_letter_file": SimpleUploadedFile("letter.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
        }

    def test_sixth_request_in_hour_is_blocked(self):
        for i in range(5):
            response = self.client.post(
                reverse("website:membership_application"), self._payload(f"111111111{i}")
            )
            self.assertEqual(response.status_code, 302)

        response = self.client.post(
            reverse("website:membership_application"), self._payload("2222222229")
        )
        self.assertEqual(response.status_code, 403)