import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from apps.authorization.choices import AccessScopeType
from apps.members.choices import FeePaymentStatus
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.members.models import Member, MembershipFee
from apps.members.services import record_fee_payment
from apps.organization.models import County, Province

User = get_user_model()


class MembershipFeeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="fee_user", password="pass12345")
        self.member = Member.objects.create(user=self.user)
        self.fee = MembershipFee.objects.create(
            member=self.member, amount=500000, due_date=datetime.date.today(),
        )

        self.manager = User.objects.create_user(username="fee_manager", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="membership.fee.update"))
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        RoleAssignment.objects.create(
            user=self.manager, role=role, access_scope=scope, start_date=datetime.date.today(),
        )

    def test_payment_does_not_change_membership_status(self):
        """قانون ۲۰ سند: Payment و Membership Status مستقل‌اند."""
        from apps.members.choices import MembershipStatus

        original_status = self.member.status
        record_fee_payment(fee=self.fee, paid_by=self.manager, payment_date=datetime.date.today())
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, original_status)

    def test_fee_marked_paid(self):
        record_fee_payment(fee=self.fee, paid_by=self.manager, payment_date=datetime.date.today())
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.payment_status, FeePaymentStatus.PAID)

    def test_unauthorized_user_cannot_record_payment(self):
        stranger = User.objects.create_user(username="fee_stranger", password="pass12345")
        with self.assertRaises(PermissionDenied):
            record_fee_payment(fee=self.fee, paid_by=stranger, payment_date=datetime.date.today())