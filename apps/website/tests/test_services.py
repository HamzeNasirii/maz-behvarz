import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from apps.authorization.choices import ApprovalStatus
from apps.employment.models import EmploymentAssignment
from apps.members.models import Member
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

from ..models import MembershipApplication
from ..services import approve_membership_application, reject_membership_application

User = get_user_model()


class MembershipApplicationServiceTests(TestCase):
    def setUp(self):
        self.approver = User.objects.create_user(username="approver_svc", password="pass12345")
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        network = HealthNetwork.objects.create(county=county, name="شبکه ساری")
        center = HealthCenter.objects.create(network=network, name="مرکز یک")
        self.house = HealthHouse.objects.create(center=center, name="خانه الف")

        self.application = MembershipApplication.objects.create(
            full_name="حمزه نصیری",
            national_code="1112223334",
            mobile_number="09120000000",
            health_house=self.house,
            accepted_terms=True,
        )

    def test_approve_creates_user_member_and_employment(self):
        user = approve_membership_application(application=self.application, approved_by=self.approver)

        self.assertEqual(user.username, "1112223334")
        self.assertTrue(Member.objects.filter(user=user).exists())
        self.assertTrue(
            EmploymentAssignment.objects.filter(
                user=user, health_house=self.house, is_primary=True
            ).exists()
        )

        self.application.refresh_from_db()
        self.assertEqual(self.application.status, ApprovalStatus.APPROVED)

    def test_cannot_approve_already_processed_application(self):
        approve_membership_application(application=self.application, approved_by=self.approver)
        with self.assertRaises(PermissionDenied):
            approve_membership_application(application=self.application, approved_by=self.approver)

    def test_reject_application(self):
        reject_membership_application(
            application=self.application, rejected_by=self.approver, note="مدارک ناقص"
        )
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, ApprovalStatus.REJECTED)
        self.assertEqual(self.application.review_note, "مدارک ناقص")


class AutoRoleAssignmentOnApprovalTests(TestCase):
    """
    ⚠️ طبق تصمیم معماری بعد از فاز ۳۵: تخصیص نقش «بهورز» دیگر بلافاصله
    هنگام تأیید اولیه‌ی عضویت اتفاق نمی‌افتد — فقط پس از تأیید کامل
    هر ۴ مدرک توسط دبیر/رئیس/نایب‌رئیس صورت می‌گیرد.
    """

    def setUp(self):
        province = Province.objects.create(name="مازندران نقش تست")
        county = County.objects.create(province=province, name="ساری نقش تست")
        network = HealthNetwork.objects.create(county=county, name="شبکه نقش تست")
        center = HealthCenter.objects.create(network=network, name="مرکز نقش تست")
        self.house = HealthHouse.objects.create(center=center, name="خانه نقش تست")

        self.approver = User.objects.create_superuser(
            username="role_approver", password="pass12345", email="a@a.com"
        )
        self.application = MembershipApplication.objects.create(
            full_name="متقاضی نقش تست", national_code="1112223338", mobile_number="09120000008",
            health_house=self.house, accepted_terms=True,
        )

    def _upload_all_documents(self, member):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.members.models import MemberBirthCertificatePage

        member.legal_decree_file = SimpleUploadedFile("decree.pdf", b"fake", content_type="application/pdf")
        member.network_letter_file = SimpleUploadedFile("letter.pdf", b"fake", content_type="application/pdf")
        member.national_id_card_file = SimpleUploadedFile("id.jpg", b"fake", content_type="image/jpeg")
        member.save()
        MemberBirthCertificatePage.objects.create(
            member=member, image=SimpleUploadedFile("bc.jpg", b"fake", content_type="image/jpeg"),
        )

    def test_no_role_assigned_immediately_on_initial_approval(self):
        from apps.authorization.models import RoleAssignment

        user = approve_membership_application(application=self.application, approved_by=self.approver)
        self.assertFalse(RoleAssignment.objects.filter(user=user, role__code="BEHVARZ").exists())

    def test_behvarz_role_assigned_only_after_all_documents_approved(self):
        from apps.authorization.models import RoleAssignment
        from apps.members.services import approve_single_document

        user = approve_membership_application(application=self.application, approved_by=self.approver)
        member = user.member_profile
        self._upload_all_documents(member)
        member.refresh_from_db()

        for key in ["legal_decree", "network_letter", "national_id", "birth_certificate"]:
            approve_single_document(member=member, actor=self.approver, document_key=key)
            member.refresh_from_db()

        assignment = RoleAssignment.objects.get(user=user, role__code="BEHVARZ")
        self.assertEqual(assignment.access_scope.house, self.house)
        self.assertIsNotNone(member.documents_verified_at)

    def test_shared_access_scope_reused_for_same_house(self):
        """دو عضو در یک خانه‌بهداشت، پس از تأیید کامل مدارک، باید از یک AccessScope مشترک استفاده کنند."""
        from apps.authorization.models import RoleAssignment
        from apps.members.services import approve_single_document

        user1 = approve_membership_application(application=self.application, approved_by=self.approver)
        member1 = user1.member_profile
        self._upload_all_documents(member1)
        member1.refresh_from_db()
        for key in ["legal_decree", "network_letter", "national_id", "birth_certificate"]:
            approve_single_document(member=member1, actor=self.approver, document_key=key)
            member1.refresh_from_db()

        application2 = MembershipApplication.objects.create(
            full_name="متقاضی دوم", national_code="1112223339", mobile_number="09120000009",
            health_house=self.house, accepted_terms=True,
        )
        user2 = approve_membership_application(application=application2, approved_by=self.approver)
        member2 = user2.member_profile
        self._upload_all_documents(member2)
        member2.refresh_from_db()
        for key in ["legal_decree", "network_letter", "national_id", "birth_certificate"]:
            approve_single_document(member=member2, actor=self.approver, document_key=key)
            member2.refresh_from_db()

        scope1 = RoleAssignment.objects.get(user=user1, role__code="BEHVARZ").access_scope
        scope2 = RoleAssignment.objects.get(user=user2, role__code="BEHVARZ").access_scope
        self.assertEqual(scope1.pk, scope2.pk)