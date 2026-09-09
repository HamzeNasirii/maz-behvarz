import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.public_content.choices import ContentStatus
from apps.public_content.models import (
    Announcement,
    Event,
    NewsArticle,
    PublicDocument,
)

User = get_user_model()


class AnnouncementQuerySetTests(TestCase):
    def test_unpublished_announcement_excluded(self):
        Announcement.objects.create(
            title="پیش‌نویس", slug="draft-1", content="...", is_published=False
        )
        self.assertEqual(Announcement.objects.published().count(), 0)

    def test_future_publish_at_excluded(self):
        Announcement.objects.create(
            title="آینده", slug="future-1", content="...", is_published=True,
            publish_at=timezone.now() + datetime.timedelta(days=1),
        )
        self.assertEqual(Announcement.objects.published().count(), 0)

    def test_published_announcement_included(self):
        Announcement.objects.create(
            title="منتشرشده", slug="pub-1", content="...", is_published=True,
            publish_at=timezone.now() - datetime.timedelta(days=1),
        )
        self.assertEqual(Announcement.objects.published().count(), 1)


class NewsArticleQuerySetTests(TestCase):
    def test_draft_excluded_from_published(self):
        NewsArticle.objects.create(
            title="خبر پیش‌نویس", slug="draft-news", content="...", status=ContentStatus.DRAFT
        )
        self.assertEqual(NewsArticle.objects.published().count(), 0)

    def test_scheduled_future_excluded(self):
        NewsArticle.objects.create(
            title="خبر زمان‌بندی‌شده", slug="scheduled-news", content="...",
            status=ContentStatus.PUBLISHED,
            published_at=timezone.now() + datetime.timedelta(hours=1),
        )
        self.assertEqual(NewsArticle.objects.published().count(), 0)

    def test_published_news_visible(self):
        NewsArticle.objects.create(
            title="خبر منتشرشده", slug="live-news", content="...",
            status=ContentStatus.PUBLISHED,
            published_at=timezone.now() - datetime.timedelta(hours=1),
        )
        self.assertEqual(NewsArticle.objects.published().count(), 1)

    def test_archived_excluded(self):
        NewsArticle.objects.create(
            title="خبر بایگانی", slug="archived-news", content="...", status=ContentStatus.ARCHIVED
        )
        self.assertEqual(NewsArticle.objects.published().count(), 0)


class EventQuerySetTests(TestCase):
    def test_past_event_excluded_from_upcoming(self):
        Event.objects.create(
            title="رویداد گذشته", slug="past-event",
            start_datetime=timezone.now() - datetime.timedelta(days=10),
            end_datetime=timezone.now() - datetime.timedelta(days=9),
            status=ContentStatus.PUBLISHED,
            published_at=timezone.now() - datetime.timedelta(days=10),
        )
        self.assertEqual(Event.objects.upcoming().count(), 0)

    def test_future_event_included_in_upcoming(self):
        Event.objects.create(
            title="رویداد آینده", slug="future-event",
            start_datetime=timezone.now() + datetime.timedelta(days=5),
            end_datetime=timezone.now() + datetime.timedelta(days=5, hours=2),
            status=ContentStatus.PUBLISHED,
            published_at=timezone.now() - datetime.timedelta(days=1),
        )
        self.assertEqual(Event.objects.upcoming().count(), 1)


class PublicDocumentQuerySetTests(TestCase):
    def _make_file(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile("doc.pdf", b"fake pdf content", content_type="application/pdf")

    def test_private_document_not_visible(self):
        PublicDocument.objects.create(
            title="سند خصوصی", file=self._make_file(), is_public=False, is_published=True
        )
        self.assertEqual(PublicDocument.objects.visible().count(), 0)

    def test_unpublished_document_not_visible(self):
        PublicDocument.objects.create(
            title="سند منتشرنشده", file=self._make_file(), is_public=True, is_published=False
        )
        self.assertEqual(PublicDocument.objects.visible().count(), 0)

    def test_public_and_published_document_visible(self):
        PublicDocument.objects.create(
            title="سند عمومی", file=self._make_file(), is_public=True, is_published=True
        )
        self.assertEqual(PublicDocument.objects.visible().count(), 1)

    def test_file_size_calculated_on_save(self):
        doc = PublicDocument.objects.create(
            title="سند با حجم", file=self._make_file(), is_public=True, is_published=True
        )
        self.assertGreater(doc.file_size, 0)