from django.db import models
from django.utils import timezone


class StatusPublishableQuerySet(models.QuerySet):
    """
    برای مدل‌هایی که از فیلد status (طبق ContentStatus) استفاده می‌کنند.
    انتشار آینده‌نگرانه (STEP 7 سند): اگر published_at در آینده باشد،
    حتی با status=published نباید عمومی نمایش داده شود.
    """

    def published(self):
        return self.filter(status="published").filter(
            models.Q(published_at__isnull=True) | models.Q(published_at__lte=timezone.now())
        )

    def draft(self):
        return self.filter(status="draft")

    def archived(self):
        return self.filter(status="archived")


class NewsArticleQuerySet(StatusPublishableQuerySet):
    def featured(self):
        return self.published().filter(is_featured=True)

    def recent(self, limit=5):
        return self.published().order_by("-published_at")[:limit]


class EventQuerySet(StatusPublishableQuerySet):
    def upcoming(self):
        return self.published().filter(end_datetime__gte=timezone.now()).order_by("start_datetime")

    def past(self):
        return self.published().filter(end_datetime__lt=timezone.now()).order_by("-start_datetime")


class AnnouncementQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True).filter(
            models.Q(publish_at__isnull=True) | models.Q(publish_at__lte=timezone.now())
        )

    def featured(self):
        return self.published().filter(is_featured=True)


class PublicDocumentQuerySet(models.QuerySet):
    def visible(self):
        """
        طبق STEP 19 سند: فقط اسنادی که هم is_public و هم is_published
        باشند قابل مشاهده در سایت عمومی‌اند.
        """
        return self.filter(is_public=True, is_published=True)


class RegulationQuerySet(StatusPublishableQuerySet):
    pass


class FAQQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True).order_by("ordering")