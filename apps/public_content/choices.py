from django.db import models


class ContentStatus(models.TextChoices):
    DRAFT = "draft", "پیش‌نویس"
    REVIEW = "review", "در حال بررسی"
    PUBLISHED = "published", "منتشرشده"
    ARCHIVED = "archived", "بایگانی‌شده"
    SCHEDULED = "scheduled", "زمان‌بندی‌شده"