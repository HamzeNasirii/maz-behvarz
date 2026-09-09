from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.authorization.services import Authorization

from . import selectors
from .forms import DocumentOptionalReasonForm, DocumentReasonForm, DocumentUploadForm
from .models import Document
from .services import (
    approve_document,
    archive_document_lifecycle,
    can_download_document,
    publish_document,
    reject_document,
    submit_document_for_review,
    upload_document,
)


@login_required
def management_list_view(request):
    if not Authorization.has_permission_code(request.user, "document.view"):
        raise PermissionDenied("شما مجوز مشاهده‌ی این فهرست را ندارید.")
    documents = selectors.documents_for_user(request.user)
    return render(request, "documents/management_list.html", {"documents": documents})


@login_required
def management_detail_view(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if not Authorization.can(request.user, "document.view", document):
        raise PermissionDenied("شما مجوز مشاهده‌ی این سند را ندارید.")
    history = document.status_history.select_related("actor").all()
    return render(request, "documents/management_detail.html", {"document": document, "history": history})


@login_required
def upload_view(request):
    if not Authorization.has_permission_code(request.user, "document.upload"):
        raise PermissionDenied("شما مجوز آپلود سند را ندارید.")

    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                document = upload_document(
                    uploaded_by=request.user,
                    title=form.cleaned_data["title"],
                    file=form.cleaned_data["file"],
                    document_type=form.cleaned_data["document_type"],
                    visibility=form.cleaned_data["visibility"],
                    scope=form.cleaned_data["scope"],
                )
                messages.success(request, "سند با موفقیت آپلود شد.")
                return redirect("documents_mgmt:detail", pk=document.pk)
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
    else:
        form = DocumentUploadForm()
    return render(request, "documents/upload.html", {"form": form})


def _handle_transition(request, pk, transition_func, requires_reason, success_message):
    document = get_object_or_404(Document, pk=pk)
    if request.method == "POST":
        form = DocumentReasonForm(request.POST) if requires_reason else DocumentOptionalReasonForm(request.POST)
        if form.is_valid():
            try:
                transition_func(document=document, actor=request.user, reason=form.cleaned_data.get("reason", ""))
                messages.success(request, success_message)
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
            return redirect("documents_mgmt:detail", pk=document.pk)
    else:
        form = DocumentReasonForm() if requires_reason else DocumentOptionalReasonForm()
    return render(request, "documents/transition_form.html", {"form": form, "document": document})


@login_required
def submit_review_view(request, pk):
    return _handle_transition(request, pk, submit_document_for_review, False, "سند برای بررسی ارسال شد.")


@login_required
def approve_view(request, pk):
    return _handle_transition(request, pk, approve_document, False, "سند تأیید شد.")


@login_required
def reject_view(request, pk):
    return _handle_transition(request, pk, reject_document, True, "سند رد شد و به پیش‌نویس بازگشت.")


@login_required
def publish_view(request, pk):
    return _handle_transition(request, pk, publish_document, False, "سند منتشر شد.")


@login_required
def archive_view(request, pk):
    return _handle_transition(request, pk, archive_document_lifecycle, False, "سند بایگانی شد.")


@login_required
def download_view(request, pk):
    """
    طبق بخش ۱۳/۱۴ سند: تنها مسیر مجاز دانلود. تغییر pk در URL نباید
    دسترسی غیرمجاز بدهد (IDOR).
    """
    document = get_object_or_404(Document, pk=pk)
    if not can_download_document(request.user, document):
        raise PermissionDenied("شما مجوز دانلود این سند را ندارید.")

    if not document.file:
        raise Http404("فایلی برای این سند ثبت نشده است.")

    response = FileResponse(
        document.file.open("rb"), as_attachment=True, filename=document.file.name.split("/")[-1]
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response