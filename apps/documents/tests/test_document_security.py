import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.authorization.choices import AccessScopeType
from apps.authorization.models import AccessScope, Permission, Role, RoleAssignment
from apps.documents.choices import DocumentStatus, DocumentVisibility
from apps.documents.models import Document
from apps.documents.services import (
    approve_document,
    can_download_document,
    publish_document,
    submit_document_for_review,
    upload_document,
)
from apps.documents.validators import validate_document_file
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

User = get_user_model()


def _pdf_file(name="test.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 fake content", content_type="application/pdf")


class DocumentFileValidationTests(TestCase):
    def test_invalid_extension_rejected(self):
        bad_file = SimpleUploadedFile("malware.exe", b"MZ", content_type="application/octet-stream")
        with self.assertRaises(ValidationError):
            validate_document_file(bad_file)

    def test_oversized_file_rejected(self):
        big_file = SimpleUploadedFile("big.pdf", b"0" * (11 * 1024 * 1024), content_type="application/pdf")
        with self.assertRaises(ValidationError):
            validate_document_file(big_file)

    def test_valid_pdf_accepted(self):
        validate_document_file(_pdf_file())

    def test_path_traversal_filename_sanitized(self):
        """طبق بخش ۱۱ سند: Django's Storage خودکار مسیر را sanitize می‌کند."""
        import datetime

        from apps.authorization.choices import AccessScopeType
        from apps.authorization.models import AccessScope, RoleAssignment

        traversal_file = _pdf_file(name="../../etc/passwd.pdf")
        user = User.objects.create_user(username="path_test_user", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="document.upload"))
        scope = AccessScope.objects.create(scope_type=AccessScopeType.GLOBAL)
        RoleAssignment.objects.create(
            user=user, role=role, access_scope=scope, start_date=datetime.date.today(),
        )

        document = upload_document(
            uploaded_by=user, title="تست مسیر", file=traversal_file,
            document_type="other", visibility=DocumentVisibility.PRIVATE,
        )
        self.assertNotIn("..", document.file.name)


class DocumentChecksumTests(TestCase):
    def setUp(self):
        import datetime

        from apps.authorization.choices import AccessScopeType
        from apps.authorization.models import AccessScope, RoleAssignment

        self.user = User.objects.create_user(username="checksum_user", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="document.upload"))
        scope = AccessScope.objects.create(scope_type=AccessScopeType.GLOBAL)
        RoleAssignment.objects.create(
            user=self.user, role=role, access_scope=scope, start_date=datetime.date.today(),
        )

    def test_checksum_computed_on_upload(self):
        document = upload_document(
            uploaded_by=self.user, title="سند تست", file=_pdf_file(),
            document_type="other", visibility=DocumentVisibility.PRIVATE,
        )
        self.assertEqual(len(document.checksum), 64)  # طول SHA-256 hex


class DocumentLifecycleTests(TestCase):
    def setUp(self):
        self.uploader = User.objects.create_user(username="doc_uploader1", password="pass12345")
        self.approver = User.objects.create_user(username="doc_approver1", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(
            Permission.objects.get(code="document.upload"),
            Permission.objects.get(code="document.approve"),
            Permission.objects.get(code="document.publish"),
            Permission.objects.get(code="document.view"),
        )
        province = Province.objects.create(name="مازندران")
        county = County.objects.create(province=province, name="ساری")
        scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=county)
        RoleAssignment.objects.create(
            user=self.uploader, role=role, access_scope=scope, start_date=datetime.date.today(),
        )
        RoleAssignment.objects.create(
            user=self.approver, role=role, access_scope=scope, start_date=datetime.date.today(),
        )

        self.document = upload_document(
            uploaded_by=self.uploader, title="آیین‌نامه تست", file=_pdf_file(),
            document_type="other", visibility=DocumentVisibility.INTERNAL, scope=scope,
        )

    def test_full_lifecycle(self):
        submit_document_for_review(document=self.document, actor=self.uploader)
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, DocumentStatus.REVIEW)

        approve_document(document=self.document, actor=self.approver)
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, DocumentStatus.APPROVED)

        publish_document(document=self.document, actor=self.approver)
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, DocumentStatus.PUBLISHED)
        self.assertIsNotNone(self.document.published_at)

    def test_uploader_cannot_approve_own_document(self):
        submit_document_for_review(document=self.document, actor=self.uploader)
        with self.assertRaises(PermissionDenied):
            approve_document(document=self.document, actor=self.uploader)


class DocumentScopeAndIDORTests(TestCase):
    def setUp(self):
        province = Province.objects.create(name="مازندران")
        self.sari = County.objects.create(province=province, name="ساری")
        babol = County.objects.create(province=province, name="بابل")

        sari_network = HealthNetwork.objects.create(county=self.sari, name="شبکه ساری سند")
        sari_center = HealthCenter.objects.create(network=sari_network, name="مرکز ساری سند")
        sari_house = HealthHouse.objects.create(center=sari_center, name="خانه ساری سند")

        babol_network = HealthNetwork.objects.create(county=babol, name="شبکه بابل سند")
        babol_center = HealthCenter.objects.create(network=babol_network, name="مرکز بابل سند")
        babol_house = HealthHouse.objects.create(center=babol_center, name="خانه بابل سند")

        self.sari_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=self.sari)
        babol_scope = AccessScope.objects.create(scope_type=AccessScopeType.COUNTY, county=babol)

        self.sari_doc = Document.objects.create(
            title="سند ساری", document_type="other", file=_pdf_file("sari.pdf"),
            visibility=DocumentVisibility.INTERNAL, scope=self.sari_scope,
        )
        self.babol_doc = Document.objects.create(
            title="سند بابل", document_type="other", file=_pdf_file("babol.pdf"),
            visibility=DocumentVisibility.INTERNAL, scope=babol_scope,
        )

        self.viewer = User.objects.create_user(username="sari_doc_viewer", password="pass12345")
        role = Role.objects.get(code="BEHVARZ")
        role.permissions.add(Permission.objects.get(code="document.view"))
        RoleAssignment.objects.create(
            user=self.viewer, role=role, access_scope=self.sari_scope, start_date=datetime.date.today(),
        )

    def test_can_view_in_scope_document(self):
        self.client.login(username="sari_doc_viewer", password="pass12345")
        response = self.client.get(reverse("documents_mgmt:detail", kwargs={"pk": self.sari_doc.pk}))
        self.assertEqual(response.status_code, 200)

    def test_idor_cannot_view_out_of_scope_document(self):
        self.client.login(username="sari_doc_viewer", password="pass12345")
        response = self.client.get(reverse("documents_mgmt:detail", kwargs={"pk": self.babol_doc.pk}))
        self.assertEqual(response.status_code, 403)

    def test_idor_cannot_download_out_of_scope_document(self):
        self.client.login(username="sari_doc_viewer", password="pass12345")
        response = self.client.get(reverse("documents_mgmt:download", kwargs={"pk": self.babol_doc.pk}))
        self.assertEqual(response.status_code, 403)

    def test_management_list_scope_aware(self):
        self.client.login(username="sari_doc_viewer", password="pass12345")
        response = self.client.get(reverse("documents_mgmt:list"))
        self.assertContains(response, "سند ساری")
        self.assertNotContains(response, "سند بابل")

    def test_unauthenticated_cannot_access_list(self):
        response = self.client.get(reverse("documents_mgmt:list"))
        self.assertEqual(response.status_code, 302)


class PublicDocumentVisibilityTests(TestCase):
    def test_private_document_excluded_from_public_selector(self):
        from apps.documents.selectors import public_documents

        Document.objects.create(
            title="سند خصوصی جدید", document_type="other", file=_pdf_file("priv.pdf"),
            status=DocumentStatus.PUBLISHED, visibility=DocumentVisibility.PRIVATE,
        )
        self.assertFalse(public_documents().filter(title="سند خصوصی جدید").exists())

    def test_published_and_public_document_visible(self):
        from apps.documents.selectors import public_documents

        Document.objects.create(
            title="سند عمومی جدید", document_type="other", file=_pdf_file("pub.pdf"),
            status=DocumentStatus.PUBLISHED, visibility=DocumentVisibility.PUBLIC,
        )
        self.assertTrue(public_documents().filter(title="سند عمومی جدید").exists())

    def test_public_but_draft_document_not_visible(self):
        """هر دو شرط (status=PUBLISHED و visibility=PUBLIC) با هم لازم است."""
        from apps.documents.selectors import public_documents

        Document.objects.create(
            title="سند پیش‌نویس عمومی", document_type="other", file=_pdf_file("draft_pub.pdf"),
            status=DocumentStatus.DRAFT, visibility=DocumentVisibility.PUBLIC,
        )
        self.assertFalse(public_documents().filter(title="سند پیش‌نویس عمومی").exists())