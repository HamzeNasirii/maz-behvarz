from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Announcement, Event, NewsArticle, Regulation


class NewsSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.7

    def items(self):
        return NewsArticle.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


class AnnouncementSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Announcement.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


class EventSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return Event.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


class RegulationSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        return Regulation.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


class StaticViewSitemap(Sitemap):
    """
    صفحات ایستای Public — طبق STEP 27 سند، فقط مسیرهای عمومی و
    قابل‌ایندکس شامل می‌شوند (بدون Admin/Dashboard/Login/Private).
    """
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return [
            "website:home",
            "website:about",
            "website:about_history",
            "website:about_mission",
            "website:about_objectives",
            "website:about_organizational_structure",
            "website:contact",
            "website:privacy",
            "website:terms",
            "public_content:news_list",
            "public_content:announcement_list",
            "public_content:event_list",
            "public_content:board",
            "public_content:committees",
            "public_content:document_list",
            "public_content:regulation_list",
            "public_content:faq",
        ]

    def location(self, item):
        return reverse(item)