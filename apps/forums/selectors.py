from .models import Forum
from .permissions import can_view_forum


def forums_for_user(user):
    if user.is_superuser:
        return Forum.objects.filter(is_active=True)
    all_forums = Forum.objects.filter(is_active=True).select_related("scope")
    accessible_ids = [f.pk for f in all_forums if can_view_forum(user, f)]
    return Forum.objects.filter(pk__in=accessible_ids)

def get_reaction_summary(user, target):
    """
    تعداد لایک/دیس‌لایک یک هدف (پست یا کامنت) + وضعیت واکنش خود کاربر
    فعلی — برای نمایش بصری، چون تا این لحظه هیچ فیدبکی به کاربر داده
    نمی‌شد (فقط در دیتابیس ذخیره می‌شد).
    """
    from django.contrib.contenttypes.models import ContentType

    from .choices import ReactionType
    from .models import ForumReaction

    content_type = ContentType.objects.get_for_model(type(target))
    reactions = ForumReaction.objects.filter(content_type=content_type, object_id=target.pk)

    user_reaction = None
    if user.is_authenticated:
        user_obj = reactions.filter(user=user).first()
        user_reaction = user_obj.reaction_type if user_obj else None

    return {
        "like_count": reactions.filter(reaction_type=ReactionType.LIKE).count(),
        "dislike_count": reactions.filter(reaction_type=ReactionType.DISLIKE).count(),
        "user_reaction": user_reaction,
    }

def get_unread_counts(user, forums):
    """
    برای هر فروم، تعداد پست‌های ایجادشده بعد از آخرین بازدید کاربر —
    اگر کاربر هرگز فروم را باز نکرده باشد، همه‌ی پست‌های آن نادیده
    محسوب می‌شوند.
    """
    from .models import ForumLastSeen, ForumPost

    last_seen_map = dict(
        ForumLastSeen.objects.filter(user=user, forum__in=forums).values_list("forum_id", "last_seen_at")
    )
    counts = {}
    for forum in forums:
        last_seen = last_seen_map.get(forum.id)
        qs = ForumPost.objects.filter(forum=forum, is_deleted=False)
        if last_seen:
            qs = qs.filter(created_at__gt=last_seen)
        counts[forum.id] = qs.count()
    return counts

