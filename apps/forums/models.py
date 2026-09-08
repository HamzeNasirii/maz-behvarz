from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .choices import ReactionType


class Forum(models.Model):
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=255, blank=True)
    scope = models.ForeignKey(
        "authorization.AccessScope", on_delete=models.PROTECT, related_name="forums",
        help_text="محدوده‌ی سازمانی این فروم (استان/شهرستان/شبکه/مرکز/خانه)",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "فروم"
        verbose_name_plural = "فروم‌ها"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ForumPost(models.Model):
    forum = models.ForeignKey(Forum, on_delete=models.PROTECT, related_name="posts")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="forum_posts")
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_pinned = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "پست فروم"
        verbose_name_plural = "پست‌های فروم"
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title


class ForumComment(models.Model):
    post = models.ForeignKey(ForumPost, on_delete=models.PROTECT, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="forum_comments")
    content = models.TextField()
    is_deleted = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies",
        verbose_name="پاسخ به کامنت",
    )
    class Meta:
        verbose_name = "کامنت فروم"
        verbose_name_plural = "کامنت‌های فروم"
        ordering = ["created_at"]

    def __str__(self):
        return f"کامنت روی {self.post}"


class ForumReaction(models.Model):
    """لایک/دیس‌لایک روی پست یا کامنت — از طریق GenericForeignKey."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="forum_reactions")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    reaction_type = models.CharField(max_length=10, choices=ReactionType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "واکنش فروم"
        verbose_name_plural = "واکنش‌های فروم"
        constraints = [
            models.UniqueConstraint(fields=["user", "content_type", "object_id"], name="uniq_reaction_per_user_per_target"),
        ]

class ForumLastSeen(models.Model):
    """
    آخرین زمانی که کاربر یک فروم را باز کرده — برای محاسبه‌ی «تعداد
    پست‌های ندیده» بدون نیاز به ردیابی تک‌تک پست‌ها.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="forum_last_seen")
    forum = models.ForeignKey(Forum, on_delete=models.CASCADE, related_name="last_seen_records")
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "آخرین بازدید فروم"
        verbose_name_plural = "آخرین بازدیدهای فروم"
        constraints = [
            models.UniqueConstraint(fields=["user", "forum"], name="uniq_last_seen_per_user_per_forum"),
        ]



