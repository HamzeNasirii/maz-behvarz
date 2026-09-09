from . import models as m

CONTENT_TYPES = {
    "news": {"model": m.NewsArticle, "label": "خبر", "can_create": True},
    "news_category": {"model": m.NewsCategory, "label": "دسته‌بندی خبر", "can_create": True},
    "hero_slide": {"model": m.HeroSlide, "label": "اسلاید هدر", "can_create": True},
    "public_document": {"model": m.PublicDocument, "label": "سند عمومی", "can_create": True},
    "document_category": {"model": m.DocumentCategory, "label": "دسته‌بندی سند", "can_create": True},
    "announcement": {"model": m.Announcement, "label": "اطلاعیه", "can_create": True},
    "event": {"model": m.Event, "label": "رویداد", "can_create": True},
    "regulation": {"model": m.Regulation, "label": "قانون و مقررات", "can_create": True},
    "faq": {"model": m.FAQ, "label": "پرسش متداول", "can_create": True},
    "faq_category": {"model": m.FAQCategory, "label": "دسته‌بندی پرسش متداول", "can_create": True},
    "contact_message": {"model": m.ContactMessage, "label": "پیام تماس", "can_create": False},
    "tag": {"model": m.Tag, "label": "تگ", "can_create": True},
}
