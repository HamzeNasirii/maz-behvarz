import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Role, RoleAssignment
from apps.authorization.role_services import transfer_role_assignment
from apps.organization.models import County, Province

User = get_user_model()


class TransferRoleAssignmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="pass12345")
        self.behvarz = Role.objects.get(code="BEHVARZ")
        self.county_rep = Role.objects.get(code="COUNTY_REPRESENTATIVE")

        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        self.babol = County.objects.create(province=province, name="بابل")

        self.sari_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        self.babol_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.babol)

        self.old_assignment = RoleAssignment.objects.create(
            user=self.user, role=self.behvarz, access_scope=self.sari_scope,
            start_date=datetime.date(2024, 1, 1),
        )

    def test_transfer_closes_old_and_creates_new(self):
        new_assignment = transfer_role_assignment(
            user=self.user,
            old_assignment=self.old_assignment,
            new_role=self.county_rep,
            new_access_scope=self.babol_scope,
            effective_date=datetime.date(2025, 1, 1),
        )

        self.old_assignment.refresh_from_db()
        self.assertFalse(self.old_assignment.is_active)
        self.assertEqual(self.old_assignment.end_date, datetime.date(2025, 1, 1))

        self.assertTrue(new_assignment.is_active)
        self.assertEqual(new_assignment.role, self.county_rep)

        # تاریخچه حفظ شده — هر دو رکورد باقی می‌مانند
        self.assertEqual(RoleAssignment.objects.for_user(self.user).count(), 2)