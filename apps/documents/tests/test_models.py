import datetime

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.documents.choices import DocumentType
from apps.documents.managers import get_documents_for
from apps.documents.models import Document
from apps.documents.services import archive_document, attach_document
from apps.members.models import Member

User = get_user_model()


class DocumentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="doc_member", password="pass12345")
        self.member = Member.objects.create(user=self.user)
        self.uploader = User.objects.create_user(username="doc_uploader", password="pass12345")

    def test_attach_document_to_member(self):
        fake_file = SimpleUploadedFile("id_card.pdf", b"fake content", content_type="application/pdf")
        document = attach_document(
            obj=self.member,
            document_type=DocumentType.NATIONAL_ID,
            file=fake_file,
            title="کارت ملی",
            uploaded_by=self.uploader,
        )
        self.assertEqual(document.content_object, self.member)

    def test_get_documents_for_member(self):
        fake_file = SimpleUploadedFile("id_card.pdf", b"fake content", content_type="application/pdf")
        attach_document(
            obj=self.member, document_type=DocumentType.NATIONAL_ID, file=fake_file,
        )
        docs = get_documents_for(self.member)
        self.assertEqual(docs.count(), 1)

    def test_archived_document_excluded_from_active_list(self):
        fake_file = SimpleUploadedFile("cert.pdf", b"fake content", content_type="application/pdf")
        document = attach_document(
            obj=self.member, document_type=DocumentType.CERTIFICATE, file=fake_file,
        )
        archive_document(document=document)
        docs = get_documents_for(self.member)
        self.assertEqual(docs.count(), 0)