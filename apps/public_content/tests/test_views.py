import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.public_content.choices import ContentStatus
from apps.public_content.models import Announcement, Event, NewsArticle


class NewsViewsTests(TestCase):
    def setUp(self):
        self.published = NewsArticle.objects.create(
            title="خبر منتشرشده", slug="news-published", content="متن کامل خبر",
            status=ContentStatus.PUBLISHED, published_at=timezone.now() - datetime.timedelta(hours=1),
        )
        NewsArticle.objects.create(
            title="خبر پیش‌نویس", slug="news-draft", content="...", status=ContentStatus.DRAFT
        )

    def test_news_list_returns_200(self):
        response = self.client.get(reverse("public_content:news_list"))
        self.assertEqual(response.status_code, 200)

    def test_draft_not_shown_in_list(self):
        response = self.client.get(reverse("public_content:news_list"))
        self.assertNotContains(response, "خبر پیش‌نویس")

    def test_news_detail_works_with_valid_slug(self):
        response = self.client.get(
            reverse("public_content:news_detail", kwargs={"slug": self.published.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "خبر منتشرشده")

    def test_invalid_slug_returns_404(self):
        response = self.client.get(
            reverse("public_content:news_detail", kwargs={"slug": "nonexistent-slug"})
        )
        self.assertEqual(response.status_code, 404)

    def test_draft_not_accessible_via_detail(self):
        response = self.client.get(
            reverse("public_content:news_detail", kwargs={"slug": "news-draft"})
        )
        self.assertEqual(response.status_code, 404)

    def test_pagination_works(self):
        for i in range(15):
            NewsArticle.objects.create(
                title=f"خبر شماره {i}", slug=f"news-{i}", content="...",
                status=ContentStatus.PUBLISHED, published_at=timezone.now() - datetime.timedelta(hours=1),
            )
        response = self.client.get(reverse("public_content:news_list"))
        self.assertTrue(response.context["page_obj"].has_next())


class AnnouncementViewsTests(TestCase):
    def test_unpublished_announcement_hidden(self):
        Announcement.objects.create(title="مخفی", slug="hidden-ann", content="...", is_published=False)
        response = self.client.get(reverse("public_content:announcement_list"))
        self.assertNotContains(response, "مخفی")

    def test_published_announcement_visible(self):
        Announcement.objects.create(
            title="نمایان", slug="visible-ann", content="...", is_published=True,
            publish_at=timezone.now() - datetime.timedelta(hours=1),
        )
        response = self.client.get(reverse("public_content:announcement_list"))
        self.assertContains(response, "نمایان")


class EventViewsTests(TestCase):
    def test_upcoming_events_displayed(self):
        Event.objects.create(
            title="رویداد آینده", slug="ev-future",
            start_datetime=timezone.now() + datetime.timedelta(days=3),
            end_datetime=timezone.now() + datetime.timedelta(days=3, hours=1),
            status=ContentStatus.PUBLISHED, published_at=timezone.now() - datetime.timedelta(hours=1),
        )
        response = self.client.get(reverse("public_content:event_list"))
        self.assertContains(response, "رویداد آینده")

    def test_past_events_excluded_from_upcoming_section(self):
        Event.objects.create(
            title="رویداد قدیمی", slug="ev-past",
            start_datetime=timezone.now() - datetime.timedelta(days=10),
            end_datetime=timezone.now() - datetime.timedelta(days=9),
            status=ContentStatus.PUBLISHED, published_at=timezone.now() - datetime.timedelta(days=10),
        )
        response = self.client.get(reverse("public_content:event_list"))
        self.assertNotIn("رویداد قدیمی", str(list(response.context["upcoming_events"])))


class ContactAndSearchTests(TestCase):
    def test_contact_form_creates_message(self):
        from apps.public_content.models import ContactMessage

        response = self.client.post(reverse("public_content:contact"), {
            "name": "تست", "email": "test@example.com", "phone": "",
            "subject": "موضوع تست", "message": "این یک پیام آزمایشی است.",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ContactMessage.objects.filter(subject="موضوع تست").exists())

    def test_search_returns_results(self):
        NewsArticle.objects.create(
            title="خبر قابل جستجو", slug="searchable-news", content="...",
            status=ContentStatus.PUBLISHED, published_at=timezone.now() - datetime.timedelta(hours=1),
        )
        response = self.client.get(reverse("public_content:search"), {"q": "قابل جستجو"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_count"], 1)

    def test_search_empty_result(self):
        response = self.client.get(reverse("public_content:search"), {"q": "چیزی که وجود ندارد"})
        self.assertEqual(response.context["total_count"], 0)