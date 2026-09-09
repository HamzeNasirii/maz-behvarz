"""
Selectors: تمام Business Rule مربوط به «چه چیزی عمومی قابل نمایش است»
این‌جا متمرکز است — طبق STEP 38 سند، Template یا View نباید این
قواعد را دوباره پیاده‌سازی کنند.
"""

from .models import Announcement, Event, FAQ, NewsArticle, PublicDocument, Regulation


def get_published_news(category_slug=None, search=None):
    from django.db.models import Q

    queryset = NewsArticle.objects.published().select_related("author").prefetch_related("categories", "tags")
    if category_slug:
        queryset = queryset.filter(categories__slug=category_slug)
    if search:
        queryset = queryset.filter(Q(title__icontains=search) | Q(summary__icontains=search))
    return queryset.distinct()


def get_featured_news(limit=3):
    return NewsArticle.objects.featured().select_related("author").prefetch_related("categories")[:limit]


def get_news_by_slug(slug):
    return NewsArticle.objects.published().select_related("author").prefetch_related(
        "categories", "tags", "gallery_images"
    ).filter(slug=slug).first()


def get_related_news(article, limit=3):
    queryset = NewsArticle.objects.published().exclude(pk=article.pk)
    category_ids = list(article.categories.values_list("pk", flat=True))
    if category_ids:
        queryset = queryset.filter(categories__pk__in=category_ids).distinct()
    return queryset.select_related("author").prefetch_related("categories")[:limit]

def get_published_announcements(featured_only=False):
    queryset = Announcement.objects.published()
    if featured_only:
        queryset = queryset.filter(is_featured=True)
    return queryset


def get_announcement_by_slug(slug):
    return Announcement.objects.published().filter(slug=slug).first()


def get_upcoming_events(limit=None):
    queryset = Event.objects.upcoming()
    return queryset[:limit] if limit else queryset


def get_past_events():
    return Event.objects.past()


def get_event_by_slug(slug):
    return Event.objects.published().filter(slug=slug).first()


def get_visible_documents(category_slug=None):
    queryset = PublicDocument.objects.visible().select_related("category")
    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)
    return queryset


def get_published_regulations():
    return Regulation.objects.published().select_related("document")


def get_regulation_by_slug(slug):
    return Regulation.objects.published().select_related("document").filter(slug=slug).first()


def get_active_faqs(category_id=None):
    queryset = FAQ.objects.active().select_related("category")
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    return queryset

def get_hero_slides(limit=5):
    from .models import HeroSlide

    return HeroSlide.objects.filter(is_active=True).order_by("-created_at")[:limit]