from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.authorization.services import Authorization
from apps.documents.managers import get_documents_for

from . import selectors
from .forms import RequestCreateForm, RequestFilterForm, RequestOptionalReasonForm, RequestReasonForm
from .models import Request
from .services import (
    approve_request,
    cancel_request,
    complete_request,
    create_request,
    reject_request,
    resubmit_request,
    return_request,
    start_request_review,
    submit_request,
)


# ---------------------------------------------------------------
# Member Portal — طبق بخش ۱۲/۵۴ سند: هرگز Request.objects.all()
# ---------------------------------------------------------------

@login_required
def portal_list_view(request):
    requests_qs = selectors.requests_for_user(request.user)

    filter_form = RequestFilterForm(request.GET or None)
    if filter_form.is_valid():
        requests_qs = selectors.filter_requests(
            requests_qs,
            status=filter_form.cleaned_data.get("status") or None,
            request_type=filter_form.cleaned_data.get("request_type") or None,
            date_from=filter_form.cleaned_data.get("date_from"),
            date_to=filter_form.cleaned_data.get("date_to"),
            search=filter_form.cleaned_data.get("q") or None,
        )

    requests_qs = selectors.sort_requests(requests_qs, request.GET.get("sort", "-created_at"))
    paginator = Paginator(requests_qs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "requests/list.html", {"page_obj": page_obj, "filter_form": filter_form})


@login_required
def portal_create_view(request):
    if request.method == "POST":
        form = RequestCreateForm(request.POST)
        if form.is_valid():
            new_request = create_request(
                requester=request.user,
                request_type=form.cleaned_data["request_type"],
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
            )
            messages.success(request, "درخواست ایجاد شد. برای ارسال، دکمه‌ی «ارسال درخواست» را بزنید.")
            return redirect("requests_portal:detail", pk=new_request.pk)
    else:
        form = RequestCreateForm()
    return render(request, "requests/create.html", {"form": form})


@login_required
def portal_detail_view(request, pk):
    request_obj = get_object_or_404(Request, pk=pk)
    if request_obj.requester_id != request.user.id:
        raise PermissionDenied("این درخواست متعلق به شما نیست.")

    history = selectors.request_history(request_obj)
    attachments = get_documents_for(request_obj)
    return render(request, "requests/detail.html", {
        "request_obj": request_obj, "history": history, "attachments": attachments,
    })


@login_required
def portal_submit_view(request, pk):
    request_obj = get_object_or_404(Request, pk=pk)
    if request_obj.requester_id != request.user.id:
        raise PermissionDenied("این درخواست متعلق به شما نیست.")
    try:
        submit_request(request_obj=request_obj, actor=request.user)
        messages.success(request, "درخواست شما ارسال شد.")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
    return redirect("requests_portal:detail", pk=request_obj.pk)


@login_required
def portal_resubmit_view(request, pk):
    request_obj = get_object_or_404(Request, pk=pk)
    if request_obj.requester_id != request.user.id:
        raise PermissionDenied("این درخواست متعلق به شما نیست.")
    try:
        resubmit_request(request_obj=request_obj, actor=request.user)
        messages.success(request, "درخواست شما دوباره ارسال شد.")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
    return redirect("requests_portal:detail", pk=request_obj.pk)


@login_required
def portal_cancel_view(request, pk):
    request_obj = get_object_or_404(Request, pk=pk)
    if request_obj.requester_id != request.user.id:
        raise PermissionDenied("این درخواست متعلق به شما نیست.")
    if request.method == "POST":
        form = RequestOptionalReasonForm(request.POST)
        if form.is_valid():
            try:
                cancel_request(request_obj=request_obj, actor=request.user, reason=form.cleaned_data["reason"])
                messages.success(request, "درخواست لغو شد.")
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
            return redirect("requests_portal:detail", pk=request_obj.pk)
    else:
        form = RequestOptionalReasonForm()
    return render(request, "requests/transition_form.html", {"form": form, "request_obj": request_obj})


# ---------------------------------------------------------------
# Management Portal — Scope-aware، طبق بخش ۱۳/۵۵ سند
# ---------------------------------------------------------------

@login_required
def management_list_view(request):
    if not Authorization.has_permission_code(request.user, "request.view"):
        raise PermissionDenied("شما مجوز مشاهده‌ی این فهرست را ندارید.")

    requests_qs = selectors.requests_for_management(request.user)

    filter_form = RequestFilterForm(request.GET or None)
    if filter_form.is_valid():
        requests_qs = selectors.filter_requests(
            requests_qs,
            status=filter_form.cleaned_data.get("status") or None,
            request_type=filter_form.cleaned_data.get("request_type") or None,
            date_from=filter_form.cleaned_data.get("date_from"),
            date_to=filter_form.cleaned_data.get("date_to"),
            search=filter_form.cleaned_data.get("q") or None,
        )

    requests_qs = selectors.sort_requests(requests_qs, request.GET.get("sort", "-created_at"))
    paginator = Paginator(requests_qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "requests/management_list.html", {"page_obj": page_obj, "filter_form": filter_form})


@login_required
def management_queue_view(request):
    """طبق بخش ۲۴/۱۴ سند — فقط Queueهایی که وابسته به Assignment نیستند."""
    if not Authorization.has_permission_code(request.user, "request.view"):
        raise PermissionDenied("شما مجوز مشاهده‌ی این صفحه را ندارید.")

    return render(request, "requests/management_queue.html", {
        "pending": selectors.pending_requests_for_management(request.user),
        "returned": selectors.recently_returned_queue(request.user),
        "rejected": selectors.recently_rejected_queue(request.user),
        "completed": selectors.recently_completed_queue(request.user),
    })


@login_required
def management_detail_view(request, pk):
    request_obj = get_object_or_404(Request, pk=pk)
    if not Authorization.can(request.user, "request.view", request_obj):
        raise PermissionDenied("شما مجوز مشاهده‌ی این درخواست را ندارید.")

    history = selectors.request_history(request_obj)
    attachments = get_documents_for(request_obj)
    return render(request, "requests/management_detail.html", {
        "request_obj": request_obj, "history": history, "attachments": attachments,
    })


def _handle_transition(request, pk, transition_func, requires_reason, success_message):
    request_obj = get_object_or_404(Request, pk=pk)
    if request.method == "POST":
        form = RequestReasonForm(request.POST) if requires_reason else RequestOptionalReasonForm(request.POST)
        if form.is_valid():
            try:
                transition_func(request_obj=request_obj, actor=request.user, reason=form.cleaned_data.get("reason", ""))
                messages.success(request, success_message)
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
            return redirect("requests_mgmt:detail", pk=request_obj.pk)
    else:
        form = RequestReasonForm() if requires_reason else RequestOptionalReasonForm()
    return render(request, "requests/transition_form.html", {"form": form, "request_obj": request_obj})


@login_required
def review_view(request, pk):
    return _handle_transition(request, pk, start_request_review, False, "بررسی درخواست آغاز شد.")


@login_required
def approve_view(request, pk):
    return _handle_transition(request, pk, approve_request, False, "درخواست تأیید شد.")


@login_required
def reject_view(request, pk):
    return _handle_transition(request, pk, reject_request, True, "درخواست رد شد.")


@login_required
def return_view(request, pk):
    return _handle_transition(request, pk, return_request, True, "درخواست برای اصلاح بازگردانده شد.")


@login_required
def complete_view(request, pk):
    return _handle_transition(request, pk, complete_request, False, "درخواست تکمیل شد.")


@login_required
def portal_attach_document_view(request, pk):
    """
    امکان پیوست‌کردن سند به یک درخواست، مستقیم از صفحه‌ی جزئیات —
    از همان مکانیزم عمومی apps.documents (Reuse، بدون مدل جدید).
    """
    from apps.documents.services import upload_document

    request_obj = get_object_or_404(Request, pk=pk)
    if request_obj.requester_id != request.user.id:
        raise PermissionDenied("این درخواست متعلق به شما نیست.")

    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]
        try:
            upload_document(
                uploaded_by=request.user,
                title=uploaded_file.name,
                file=uploaded_file,
                document_type="other",
                visibility="private",
                scope=request_obj.scope,
            )
            # اتصال سند تازه‌آپلودشده به همین درخواست (Reuse از GenericForeignKey موجود)
            from apps.documents.models import Document
            last_doc = Document.objects.filter(uploaded_by=request.user).order_by("-created_at").first()
            if last_doc:
                last_doc.content_object = request_obj
                last_doc.save(update_fields=["content_type", "object_id"])
            messages.success(request, "سند با موفقیت پیوست شد.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, str(exc))

    return redirect("requests_portal:detail", pk=pk)