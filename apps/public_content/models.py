from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from .choices import ContentStatus
from .managers import (
    AnnouncementQuerySet,
    EventQuerySet,
    FAQQuerySet,
    NewsArticleQuerySet,
    PublicDocumentQuerySet,
    RegulationQuerySet,
)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class HeroSlide(TimeStampedModel):
    title = models.CharField(max_length=150)
    subtitle = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="public_content/hero/%Y/%m/", blank=True, null=True)
    cta_text = models.CharField(max_length=50, blank=True)
    cta_link = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    ordering = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "اسلاید هدر"
        verbose_name_plural = "اسلایدهای هدر"
        ordering = ["ordering", "-created_at"]

    def __str__(self):
        return self.title


class Announcement(TimeStampedModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    summary = models.CharField(max_length=300, blank=True)
    content = models.TextField()
    publish_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    objects = AnnouncementQuerySet.as_manager()

    class Meta:
        verbose_name = "اطلاعیه"
        verbose_name_plural = "اطلاعیه‌ها"
        ordering = ["-publish_at", "-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("public_content:announcement_detail", kwargs={"slug": self.slug})


class NewsCategory(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        verbose_name = "دسته‌بندی خبر"
        verbose_name_plural = "دسته‌بندی‌های خبر"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        verbose_name = "تگ"
        verbose_name_plural = "تگ‌ها"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=False)
            if not base:
                import time
                base = f"tag-{int(time.time())}"
            self.slug = base
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class NewsArticle(TimeStampedModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    summary = models.CharField(max_length=300, blank=True)
    content = models.TextField()
    featured_image = models.ImageField(upload_to="public_content/news/%Y/%m/", blank=True, null=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="news_articles",
    )
    categories = models.ManyToManyField(
        NewsCategory, blank=True, related_name="news_articles_multi",
        verbose_name="دسته‌بندی‌ها",
    )
    tags = models.ManyToManyField(
        Tag, blank=True, related_name="tagged_news", verbose_name="تگ‌ها",
    )
    status = models.CharField(
        max_length=20, choices=ContentStatus.choices, default=ContentStatus.DRAFT, db_index=True
    )
    is_featured = models.BooleanField(default=False, db_index=True)
    view_count = models.PositiveIntegerField(default=0, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = NewsArticleQuerySet.as_manager()

    class Meta:
        verbose_name = "خبر"
        verbose_name_plural = "اخبار"
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    @property
    def estimated_reading_minutes(self):
        word_count = len(self.content.split())
        # سرعت متوسط مطالعه‌ی فارسی: حدود ۱۵۰-۲۰۰ کلمه در دقیقه
        minutes = max(1, round(word_count / 180))
        return minutes

    @property
    def author_position_display(self):
        """
        سمت نویسنده در هیئت‌مدیره (اگر داشته باشد) — مثل «خزانه‌دار»،
        برای نمایش کنار نام او در صفحه‌ی خبر.
        """
        if not self.author_id:
            return None
        from apps.board.models import BoardMembership

        membership = BoardMembership.objects.filter(user_id=self.author_id, is_active=True).first()
        return membership.get_position_display() if membership else None

    def get_absolute_url(self):
        return reverse("public_content:news_detail", kwargs={"slug": self.slug})


class Event(TimeStampedModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField(db_index=True)
    location = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to="public_content/events/%Y/%m/", blank=True, null=True)
    registration_required = models.BooleanField(default=False)
    registration_url = models.URLField(blank=True)
    status = models.CharField(
        max_length=20, choices=ContentStatus.choices, default=ContentStatus.DRAFT, db_index=True
    )
    published_at = models.DateTimeField(null=True, blank=True)

    objects = EventQuerySet.as_manager()

    class Meta:
        verbose_name = "رویداد"
        verbose_name_plural = "رویدادها"
        ordering = ["start_datetime"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_datetime__gte=models.F("start_datetime")),
                name="event_end_after_start",
            ),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("public_content:event_detail", kwargs={"slug": self.slug})


class DocumentCategory(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        verbose_name = "دسته‌بندی سند"
        verbose_name_plural = "دسته‌بندی‌های سند"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PublicDocument(TimeStampedModel):
    """
    مستقل از apps.documents.Document (که Polymorphic و پیوست‌شده به
    Member/EmploymentAssignment است). این مدل مخصوص اسناد رسمی و
    عمومی سایت (اساسنامه، آیین‌نامه، بخشنامه، ...) است.
    """

    title = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True)
    category = models.ForeignKey(
        DocumentCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )
    file = models.FileField(upload_to="public_content/documents/%Y/%m/")
    file_type = models.CharField(max_length=20, blank=True)
    categories = models.ManyToManyField(
        DocumentCategory, blank=True, related_name="documents_multi", verbose_name="دسته‌بندی‌ها",
    )
    file_size = models.PositiveIntegerField(default=0, help_text="حجم فایل به بایت")
    publication_date = models.DateField(null=True, blank=True)
    is_public = models.BooleanField(default=False, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)

    objects = PublicDocumentQuerySet.as_manager()

    class Meta:
        verbose_name = "سند عمومی"
        verbose_name_plural = "اسناد عمومی"
        ordering = ["-publication_date", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except (ValueError, OSError):
                pass
        super().save(*args, **kwargs)

class PublicDocumentFile(models.Model):
    document = models.ForeignKey(
        PublicDocument, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="public_content/document_files/%Y/%m/")
    title = models.CharField(max_length=200, blank=True)
    file_size = models.PositiveIntegerField(default=0, help_text="حجم فایل به بایت")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "فایل پیوست سند"
        verbose_name_plural = "فایل‌های پیوست سند"
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except (ValueError, OSError):
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title or f"فایل {self.document} ({self.pk})"

class Regulation(TimeStampedModel):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    summary = models.CharField(max_length=300, blank=True)
    content = models.TextField(blank=True)
    document = models.ForeignKey(
        PublicDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name="regulations"
    )
    effective_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=ContentStatus.choices, default=ContentStatus.DRAFT, db_index=True
    )
    published_at = models.DateTimeField(null=True, blank=True)

    objects = RegulationQuerySet.as_manager()

    class Meta:
        verbose_name = "قانون و مقررات"
        verbose_name_plural = "قوانین و مقررات"
        ordering = ["-effective_date"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("public_content:regulation_detail", kwargs={"slug": self.slug})


class FAQCategory(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "دسته‌بندی پرسش متداول"
        verbose_name_plural = "دسته‌بندی‌های پرسش متداول"
        ordering = ["name"]

    def __str__(self):
        return self.name


class FAQ(TimeStampedModel):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    category = models.ForeignKey(
        FAQCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="faqs"
    )
    ordering = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    objects = FAQQuerySet.as_manager()

    class Meta:
        verbose_name = "پرسش متداول"
        verbose_name_plural = "پرسش‌های متداول"
        ordering = ["ordering", "question"]

    def __str__(self):
        return self.question


class ContactMessage(TimeStampedModel):
    """
    طبق STEP 23 سند، پیام‌های تماس مستقیم به ایمیل ارسال نمی‌شوند؛
    ابتدا این‌جا ذخیره می‌شوند و از طریق Admin بررسی می‌شوند.
    """

    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = "پیام تماس"
        verbose_name_plural = "پیام‌های تماس"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} — {self.name}"




class NewsImage(models.Model):
    news_article = models.ForeignKey(
        "NewsArticle", on_delete=models.CASCADE, related_name="gallery_images"
    )
    image = models.ImageField(upload_to="public_content/news_gallery/%Y/%m/")
    caption = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "تصویر گالری خبر"
        verbose_name_plural = "تصاویر گالری خبر"
        ordering = ["created_at"]

    def __str__(self):
        return f"تصویر {self.news_article} ({self.pk})"
