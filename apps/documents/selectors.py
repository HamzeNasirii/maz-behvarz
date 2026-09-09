from .choices import DocumentStatus, DocumentVisibility
from .managers import get_documents_for  # حفظ سازگاری با فاز ۱۶
from .models import Document


def public_documents():
    """
    طبق بخش ۲۴ سند: سند فقط با status=PUBLISHED **و** visibility=PUBLIC
    عمومی است.
    """
    return Document.objects.filter(
        status=DocumentStatus.PUBLISHED, visibility=DocumentVisibility.PUBLIC, is_archived=False,
    )


def documents_for_user(user):
    from apps.authorization.services import Authorization

    return Authorization.scope_queryset(user, Document.objects.filter(is_archived=False))


def documents_pending_review(user):
    from apps.authorization.services import Authorization

    queryset = Document.objects.filter(status=DocumentStatus.REVIEW)
    return Authorization.scope_queryset(user, queryset)