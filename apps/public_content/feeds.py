from django.contrib.syndication.views import Feed
from django.urls import reverse

from .selectors import get_published_news


class LatestNewsFeed(Feed):
    title = "اخبار انجمن صنفی بهورزان استان مازندران"
    link = "/news/"
    description = "آخرین اخبار منتشرشده در سایت انجمن"

    def items(self):
        return get_published_news()[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.summary or item.content[:200]

    def item_link(self, item):
        return item.get_absolute_url()

    def item_pubdate(self, item):
        return item.published_at or item.created_at