from django.core.exceptions import PermissionDenied
from django.db import transaction

from .models import ForumComment, ForumPost, ForumReaction
from .permissions import can_moderate_forum, can_post_in_forum, can_view_forum


@transaction.atomic
def create_post(*, forum, author, title, content):
    if not can_post_in_forum(author, forum):
        raise PermissionDenied("شما به این فروم دسترسی ندارید.")
    return ForumPost.objects.create(forum=forum, author=author, title=title, content=content)


@transaction.atomic
def add_comment(*, post, author, content, parent=None):
    if not can_view_forum(author, post.forum):
        raise PermissionDenied("شما به این فروم دسترسی ندارید.")
    if parent is not None and parent.post_id != post.id:
        raise PermissionDenied("کامنت والد متعلق به این پست نیست.")
    return ForumComment.objects.create(post=post, author=author, content=content, parent=parent)


@transaction.atomic
def toggle_reaction(*, user, target, reaction_type):
    from django.contrib.contenttypes.models import ContentType

    content_type = ContentType.objects.get_for_model(type(target))
    existing = ForumReaction.objects.filter(user=user, content_type=content_type, object_id=target.pk).first()

    if existing and existing.reaction_type == reaction_type:
        existing.delete()
        return None
    elif existing:
        existing.reaction_type = reaction_type
        existing.save(update_fields=["reaction_type"])
        return existing
    else:
        return ForumReaction.objects.create(
            user=user, content_type=content_type, object_id=target.pk, reaction_type=reaction_type,
        )


@transaction.atomic
def delete_post(*, post, actor):
    if not can_moderate_forum(actor, post.forum):
        raise PermissionDenied("شما مجوز حذف این پست را ندارید.")
    post.is_deleted = True
    post.save(update_fields=["is_deleted"])


@transaction.atomic
def delete_comment(*, comment, actor):
    if not can_moderate_forum(actor, comment.post.forum):
        raise PermissionDenied("شما مجوز حذف این کامنت را ندارید.")
    comment.is_deleted = True
    comment.save(update_fields=["is_deleted"])