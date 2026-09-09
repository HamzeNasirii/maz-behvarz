from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.authorization.services import Authorization

from .choices import ALLOWED_DOCUMENT_TRANSITIONS, DocumentStatus
from .models import Document, DocumentStatusHistory
from .validators import compute_file_checksum, validate_document_file


@transaction.atomic
def upload_document(*, uploaded_by, title, file, document_type, visibility, scope=None):
    if not Authorization.has_permission_code(uploaded_by, "document.upload"):
        raise PermissionDenied("این کاربر مجوز آپلود سند را ندارد.")

    validate_document_file(file)
    checksum = compute_file_checksum(file)

    document = Document(
        document_type=document_type,
        file=file,
        title=title,
        visibility=visibility,
        scope=scope,
        uploaded_by=uploaded_by,
        checksum=checksum,
        file_size=file.size,
        mime_type=getattr(file, "content_type", "") or "",
    )
    document.save()
    return document


def _transition(*, document, new_status, actor, reason=""):
    allowed = ALLOWED_DOCUMENT_TRANSITIONS.get(document.status, set())
    if new_status not in allowed:
        raise ValidationError(f"تغییر وضعیت از «{document.get_status_display()}» به این وضعیت مجاز نیست.")

    DocumentStatusHistory.objects.create(
        document=document, previous_status=document.status, new_status=new_status, actor=actor, reason=reason,
    )
    document.status = new_status
    if new_status == DocumentStatus.PUBLISHED:
        document.published_at = timezone.now()
    if new_status == DocumentStatus.ARCHIVED:
        document.archived_at = timezone.now()
        document.is_archived = True
    document.save(update_fields=["status", "published_at", "archived_at", "is_archived", "updated_at"])
    return document


@transaction.atomic
def submit_document_for_review(*, document, actor, reason=""):
    if document.uploaded_by_id != actor.id and not Authorization.can(actor, "document.update", document):
        raise PermissionDenied("این کاربر مجوز ارسال این سند برای بررسی را ندارد.")
    return _transition(document=document, new_status=DocumentStatus.REVIEW, actor=actor, reason=reason)


@transaction.atomic
def approve_document(*, document, actor, reason=""):
    if not Authorization.can(actor, "document.approve", document):
        raise PermissionDenied("این کاربر مجوز تأیید این سند را ندارد.")
    if document.uploaded_by_id == actor.id:
        raise PermissionDenied("آپلودکننده نمی‌تواند تأییدکننده‌ی همان سند باشد.")
    return _transition(document=document, new_status=DocumentStatus.APPROVED, actor=actor, reason=reason)


@transaction.atomic
def reject_document(*, document, actor, reason):
    if not reason:
        raise ValidationError("ثبت دلیل رد الزامی است.")
    if not Authorization.can(actor, "document.approve", document):
        raise PermissionDenied("این کاربر مجوز رد این سند را ندارد.")
    return _transition(document=document, new_status=DocumentStatus.DRAFT, actor=actor, reason=reason)


@transaction.atomic
def publish_document(*, document, actor, reason=""):
    if not Authorization.can(actor, "document.publish", document):
        raise PermissionDenied("این کاربر مجوز انتشار این سند را ندارد.")
    return _transition(document=document, new_status=DocumentStatus.PUBLISHED, actor=actor, reason=reason)


@transaction.atomic
def archive_document_lifecycle(*, document, actor, reason=""):
    if not Authorization.can(actor, "document.delete", document):
        raise PermissionDenied("این کاربر مجوز بایگانی این سند را ندارد.")
    return _transition(document=document, new_status=DocumentStatus.ARCHIVED, actor=actor, reason=reason)


def can_download_document(user, document):
    """
    بررسی مرکزی امنیت دانلود (بخش ۱۳ سند): Authentication (در View با
    login_required)، Permission+Scope+Object Authorization از طریق
    Authorization.can() موجود. سند PUBLIC منتشرشده استثنای صریح دارد.
    """
    if document.visibility == "public" and document.status == "published":
        return True
    return Authorization.can(user, "document.view", document)


# --- توابع قدیمی فاز ۱۶ (بدون تغییر، برای سازگاری عقب‌رو) ---
@transaction.atomic
def attach_document(*, obj, document_type, file, title="", uploaded_by=None):
    return Document.objects.create(
        content_object=obj, document_type=document_type, file=file, title=title, uploaded_by=uploaded_by,
    )


@transaction.atomic
def archive_document(*, document):
    document.is_archived = True
    document.save(update_fields=["is_archived", "updated_at"])
    return document