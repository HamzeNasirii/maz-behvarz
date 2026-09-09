from django.contrib import admin
from django.utils.html import format_html

from . import models as m
from .models import (
    Announcement,
    ContactMessage,
    DocumentCategory,
    Event,
    FAQ,
    FAQCategory,
    HeroSlide,
    NewsArticle,
    NewsCategory,
    PublicDocument,
    Regulation,
)


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "ordering", "image_preview")
    list_filter = ("is_active",)
    search_fields = ("title",)
    ordering = ("ordering",)

    @admin.display(description="پیش‌نمایش")
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:40px;" />', obj.image.url)
        return "-"


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "is_featured", "publish_at", "created_at")
    list_filter = ("is_published", "is_featured")
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "created_at"


@admin.register(NewsCategory)
class NewsCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "categories_display", "status", "is_featured", "published_at", "author", "image_preview")
    list_filter = ("status", "is_featured", "categories")
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"
    autocomplete_fields = ("author", "categories", "tags")
    readonly_fields = ("image_preview",)

    @admin.display(description="پیش‌نمایش تصویر")
    def image_preview(self, obj):
        if obj.featured_image:
            return format_html('<img src="{}" style="height:60px;" />', obj.featured_image.url)
        return "-"

    def categories_display(self, obj):
        return "، ".join(c.name for c in obj.categories.all())
    categories_display.short_description = "دسته‌بندی‌ها"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "start_datetime", "end_datetime", "registration_required")
    list_filter = ("status", "registration_required")
    search_fields = ("title", "location")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "start_datetime"


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PublicDocument)
class PublicDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_public", "is_published", "publication_date", "file_size")
    list_filter = ("is_public", "is_published", "category")
    search_fields = ("title", "description")
    autocomplete_fields = ("category",)
    readonly_fields = ("file_size",)
    date_hierarchy = "publication_date"


@admin.register(Regulation)
class RegulationAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "effective_date")
    list_filter = ("status",)
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("document",)


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "ordering", "is_active")
    list_filter = ("is_active", "category")
    search_fields = ("question", "answer")
    ordering = ("ordering",)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("name", "email", "subject")
    readonly_fields = ("name", "email", "phone", "subject", "message", "created_at")
    date_hierarchy = "created_at"


@admin.register(m.Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)