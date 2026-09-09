"""
Selectors برای Membership — همه Scope-aware از طریق for_user().
"""

from .models import Member

def _members_queryset_for(user):
    """
    Reviewerهای Scope-محدود همچنان از Member.objects.for_user() (که
    Authorization.scope_queryset را صدا می‌زند) عبور می‌کنند؛ اما
    رئیس/دبیر/Staff به همه‌ی اعضا دسترسی کامل دارند.
    """
    from .permissions import can_manage_members

    if can_manage_members(user):
        return Member.objects.all()
    return Member.objects.for_user(user)

def active_memberships(user):
    return _members_queryset_for(user).active()


def pending_review_memberships(user):
    return _members_queryset_for(user).pending_review()


def suspended_memberships(user):
    return _members_queryset_for(user).suspended()


def expired_memberships(user):
    return _members_queryset_for(user).expired()

def members_awaiting_document_verification(user):
    return _members_queryset_for(user).filter(
        status="active", documents_verified_at__isnull=True,
    ).select_related("user")