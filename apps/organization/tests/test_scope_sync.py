from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province
from apps.organization.scope_sync import ensure_access_scope_for

User = get_user_model()


class ScopeSyncTests(TestCase):
    def setUp(self):
        self.province = Province.objects.create(name="مازندران Scope Sync تست")

    def test_ensure_creates_scope_once(self):
        scope1 = ensure_access_scope_for("province", self.province)
        scope2 = ensure_access_scope_for("province", self.province)
        self.assertEqual(scope1.pk, scope2.pk)
        self.assertEqual(
            AccessScope.objects.filter(scope_type=AccessScopeType.PROVINCE, province=self.province).count(), 1
        )


class ScopeAutoCreationOnOrgCreateViewTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username="scope_view_staff", password="pass12345", is_staff=True)
        self.province = Province.objects.create(name="استان Scope View تست")

    def test_creating_county_via_view_creates_scope(self):
        self.client.login(username="scope_view_staff", password="pass12345")
        self.client.post(
            reverse("org_mgmt:create", kwargs={"level": "county"}) + f"?parent={self.province.id}",
            {"name": "شهرستان Scope View تست", "code": "", "is_active": "on"},
        )
        county = County.objects.get(name="شهرستان Scope View تست")
        self.assertTrue(
            AccessScope.objects.filter(scope_type=AccessScopeType.COUNTY, county=county).exists()
        )

    def test_no_duplicate_scope_on_repeated_creation_attempt(self):
        """حتی اگر ensure_access_scope_for چندبار روی همان رکورد صدا زده شود، تکراری نمی‌سازد."""
        county = County.objects.create(province=self.province, name="شهرستان تکراری تست")
        ensure_access_scope_for("county", county)
        ensure_access_scope_for("county", county)
        self.assertEqual(
            AccessScope.objects.filter(scope_type=AccessScopeType.COUNTY, county=county).count(), 1
        )


class BackfillCommandTests(TestCase):
    def test_backfill_command_creates_missing_scopes(self):
        from django.core.management import call_command

        province = Province.objects.create(name="استان Backfill تست")
        county = County.objects.create(province=province, name="شهرستان Backfill تست")

        # قبل از Backfill، هیچ Scope‌ای نباید وجود داشته باشد
        self.assertFalse(AccessScope.objects.filter(scope_type=AccessScopeType.COUNTY, county=county).exists())

        call_command("backfill_access_scopes")

        self.assertTrue(AccessScope.objects.filter(scope_type=AccessScopeType.PROVINCE, province=province).exists())
        self.assertTrue(AccessScope.objects.filter(scope_type=AccessScopeType.COUNTY, county=county).exists())