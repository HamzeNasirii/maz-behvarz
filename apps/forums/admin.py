from django.contrib import admin

from .models import Forum, ForumComment, ForumPost, ForumReaction


@admin.register(Forum)
class ForumAdmin(admin.ModelAdmin):
    list_display = ("name", "scope", "is_active")
    autocomplete_fields = ("scope",)


@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display = ("title", "forum", "author", "is_pinned", "is_deleted", "created_at")
    list_filter = ("is_pinned", "is_deleted", "forum")


@admin.register(ForumComment)
class ForumCommentAdmin(admin.ModelAdmin):
    list_display = ("post", "author", "is_deleted", "created_at")


admin.site.register(ForumReaction)