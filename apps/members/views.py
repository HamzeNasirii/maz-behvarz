from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.db import models

from apps.authorization.models import RoleAssignment
from apps.authorization.services import Authorization
from apps.employment.models import EmploymentAssignment
from apps.board.permissions import is_board_leadership, is_board_member

from .forms import ProfileEditForm, MemberDocumentsForm, MemberRemovalProposalForm, RemovalDecisionForm, \
    MemberContactForm, ForcedPasswordChangeForm
from .models import Member, MembershipFee, MemberRemovalProposal
from .services import approve_member_removal, propose_member_removal, reject_member_removal


@login_required
def portal_dashboard_view(request):
    """
    این View همیشه فقط پروفایل خود کاربر لاگین‌شده را نشان می‌دهد،
    پس نیازی به عبور از Authorization Engine نیست — مالکیت در همین
    کوئری (request.user.member_profile) تضمین شده است.
    """
    if request.user.is_staff or request.user.is_superuser:
        return redirect("reports:dashboard")

    try:
        member = request.user.member_profile
    except Member.DoesNotExist:
        member = None

    active_period = None
    if member is not None:
        active_period = member.membership_periods.filter(is_active=True).order_by("-start_date").first()

    active_employments = (
        EmploymentAssignment.objects.for_user(request.user)
        .active()
        .select_related("health_house", "health_house__center", "health_house__center__network",
                        "health_house__center__network__county",
                        "health_house__center__network__county__province")
    )

    active_roles = (
        RoleAssignment.objects.for_user(request.user)
        .active()
        .select_related("role", "access_scope")
    )

    return render(
        request,
        "members/portal_dashboard.html",
        {
            "member": member,
            "active_period": active_period,
            "active_employments": active_employments,
            "active_roles": active_roles,
        },
    )


@login_required
def portal_employment_history_view(request):
    assignments = (
        EmploymentAssignment.objects.for_user(request.user)
        .select_related("health_house", "health_house__center")
        .order_by("-start_date")
    )
    return render(request, "members/portal_employment_history.html", {"assignments": assignments})


@login_required
def profile_view(request):
    return render(request, "members/profile.html", {"profile_user": request.user})


@login_required
def profile_edit_view(request):
    try:
        member = request.user.member_profile
    except Member.DoesNotExist:
        member = None

    if request.method == "POST":
        if request.POST.get("remove_picture"):
            request.user.profile_picture.delete(save=False)
            request.user.profile_picture = None
            request.user.save(update_fields=["profile_picture"])
            messages.success(request, "تصویر پروفایل حذف شد.")
            return redirect("members_portal:profile_edit")

        user_form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        contact_form = MemberContactForm(request.POST, instance=member) if member else None

        user_valid = user_form.is_valid()
        contact_valid = contact_form.is_valid() if contact_form else True

        if user_valid and contact_valid:
            user_form.save()
            if contact_form:
                contact_form.save()
            messages.success(request, "اطلاعات پروفایل با موفقیت به‌روزرسانی شد.")
            return redirect("members_portal:profile")
    else:
        user_form = ProfileEditForm(instance=request.user)
        contact_form = MemberContactForm(instance=member) if member else None

    return render(request, "members/profile_edit.html", {"user_form": user_form, "contact_form": contact_form})


@login_required
def member_list_view(request):
    from .permissions import can_manage_members

    if not can_manage_members(request.user) and not Authorization.has_permission_code(request.user, "member.view"):
        raise PermissionDenied("شما مجوز مشاهده‌ی این فهرست را ندارید.")

    query = request.GET.get("q", "").strip()
    members = selectors._members_queryset_for(request.user).select_related("user")

    if query:
        members = members.filter(
            models.Q(user__first_name__icontains=query)
            | models.Q(user__last_name__icontains=query)
            | models.Q(user__username__icontains=query)
        )

    return render(request, "members/management_list.html", {"members": members, "query": query})


@login_required
def member_detail_view(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if not _can_access_member(request.user, member):
        raise PermissionDenied("شما مجوز مشاهده‌ی این عضو را ندارید.")

    membership_periods = member.membership_periods.order_by("-start_date")
    employment_history = (
        EmploymentAssignment.objects.for_user(member.user).select_related("health_house").order_by("-start_date")
    )
    fees = member.fees.order_by("-due_date")
    status_history = member.status_history.select_related("actor").all()

    from apps.authorization.secure_links import make_ref

    return render(request, "members/management_detail.html", {
        "member": member,
        "membership_periods": membership_periods,
        "employment_history": employment_history,
        "fees": fees,
        "status_history": status_history,
        "member_user_ref": make_ref(member.user.pk),
    })


from django.core.exceptions import PermissionDenied, ValidationError

from . import selectors
from .forms import MembershipOptionalReasonForm, MembershipReasonForm
from .models import Member
from .services import (
    approve_membership,
    cancel_membership,
    expire_membership,
    reinstate_membership,
    reject_membership,
    review_membership,
    submit_membership,
    suspend_membership,
)


@login_required
def membership_status_view(request):
    """
    صفحه‌ی Read-only وضعیت عضویت خود کاربر — مالکیت از طریق
    request.user تضمین شده، نیازی به Authorization Engine نیست.
    """
    try:
        member = request.user.member_profile
    except Member.DoesNotExist:
        member = None

    history = []
    if member is not None:
        history = member.status_history.select_related("actor").all()

    return render(request, "members/membership_status.html", {"member": member, "history": history})


@login_required
def membership_apply_view(request):
    """
    برای کاربرانی که User دارند ولی هنوز Member نیستند (سناریوی نادر —
    اکثر اعضا از طریق فرم عمومی گام ۱۲/۱۵ ساخته می‌شوند).
    """
    if hasattr(request.user, "member_profile"):
        messages.info(request, "شما در حال حاضر پروفایل عضویت دارید.")
        return redirect("members_portal:membership_status")

    if request.method == "POST":
        member = Member.objects.create(user=request.user)
        submit_membership(member=member, actor=request.user)
        messages.success(request, "درخواست عضویت شما ثبت شد.")
        return redirect("members_portal:membership_status")

    return render(request, "members/membership_apply.html")


@login_required
def membership_management_list_view(request):
    from .permissions import can_manage_members
    from .services import get_document_status_rows

    if not can_manage_members(request.user) and not Authorization.has_permission_code(request.user, "membership.review"):
        raise PermissionDenied("شما مجوز مشاهده‌ی این فهرست را ندارید.")

    members = selectors.pending_review_memberships(request.user).select_related("user")
    awaiting_docs = list(selectors.members_awaiting_document_verification(request.user))
    for member in awaiting_docs:
        member.document_status_rows = get_document_status_rows(member)

    return render(request, "members/membership_management_list.html", {
        "members": members, "awaiting_docs": awaiting_docs,
    })


@login_required
def membership_management_detail_view(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if not _can_manage_membership(request.user, member, "membership.review"):
        raise PermissionDenied("شما مجوز مشاهده‌ی این عضویت را ندارید.")

    history = member.status_history.select_related("actor").all()
    return render(request, "members/membership_management_detail.html", {"member": member, "history": history})


def _handle_transition(request, pk, transition_func, requires_reason=False, success_message=""):
    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        if requires_reason:
            form = MembershipReasonForm(request.POST)
        else:
            form = MembershipOptionalReasonForm(request.POST)

        if form.is_valid():
            try:
                transition_func(member=member, actor=request.user, reason=form.cleaned_data.get("reason", ""))
                messages.success(request, success_message)
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
            return redirect("members_portal:membership_management_detail", pk=member.pk)
    else:
        form = MembershipReasonForm() if requires_reason else MembershipOptionalReasonForm()

    return render(request, "members/membership_transition_form.html", {"form": form, "member": member})


@login_required
def membership_review_view(request, pk):
    member = get_object_or_404(Member, pk=pk)
    try:
        review_membership(member=member, actor=request.user)
        messages.success(request, "بررسی درخواست آغاز شد.")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
    return redirect("members_portal:membership_management_detail", pk=member.pk)


@login_required
def membership_approve_view(request, pk):
    """
    این View هر دو گام Approve و Activate را پشت‌سرهم انجام می‌دهد
    (تصمیم عمدی برای سادگی UX)؛ توابع سرویس زیرین همچنان مستقل و
    جداگانه قابل فراخوانی و تست‌اند.
    """
    from .services import activate_membership

    member = get_object_or_404(Member, pk=pk)
    try:
        approve_membership(member=member, actor=request.user)
        activate_membership(member=member, actor=request.user)
        messages.success(request, "عضویت تأیید و فعال شد.")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
    return redirect("members_portal:membership_management_detail", pk=member.pk)


@login_required
def membership_reject_view(request, pk):
    return _handle_transition(request, pk, reject_membership, requires_reason=True,
                              success_message="درخواست عضویت رد شد.")


@login_required
def membership_suspend_view(request, pk):
    return _handle_transition(request, pk, suspend_membership, requires_reason=True,
                              success_message="عضویت به حالت تعلیق درآمد.")


@login_required
def membership_reinstate_view(request, pk):
    return _handle_transition(request, pk, reinstate_membership, requires_reason=False,
                              success_message="عضویت اعاده شد.")


@login_required
def membership_expire_view(request, pk):
    return _handle_transition(request, pk, expire_membership, requires_reason=False,
                              success_message="انقضای عضویت ثبت شد.")


@login_required
def membership_cancel_view(request, pk):
    return _handle_transition(request, pk, cancel_membership, requires_reason=True, success_message="عضویت لغو شد.")


def _can_access_member(user, member):
    from .permissions import can_manage_members

    if can_manage_members(user):
        return True
    return Authorization.can(user, "member.view", member)


def _can_manage_membership(user, member, permission_code):
    from .permissions import can_manage_members

    if can_manage_members(user):
        return True
    return Authorization.can(user, permission_code, member)


@login_required
def members_hub_view(request):
    from .permissions import can_manage_members

    if not can_manage_members(request.user) and not Authorization.has_permission_code(request.user, "member.view"):
        raise PermissionDenied("شما مجوز دسترسی به این صفحه را ندارید.")

    return render(request, "members/management_hub.html", {
        "total_members": selectors._members_queryset_for(request.user).count(),
        "pending_count": selectors.pending_review_memberships(request.user).count(),
        "unpaid_fees_count": MembershipFee.objects.filter(payment_status="unpaid").count() if can_manage_members(
            request.user) else None,
    })


@login_required
def member_documents_view(request):
    """
    ارسال/به‌روزرسانی/حذف مدارک توسط خود عضو — خودمالکیتی مستقیم از
    طریق request.user، بدون نیاز به Authorization Engine.
    """
    from .models import MemberBirthCertificatePage

    try:
        member = request.user.member_profile
    except Member.DoesNotExist:
        messages.error(request, "برای ارسال مدارک، ابتدا باید پروفایل عضویت داشته باشید.")
        return redirect("members_portal:dashboard")

    if request.method == "POST":
        remove_field = request.POST.get("remove_field")
        if remove_field in ("legal_decree_file", "network_letter_file", "national_id_card_file"):
            getattr(member, remove_field).delete(save=False)
            setattr(member, remove_field, None)
            member.save(update_fields=[remove_field, "updated_at"])
            messages.success(request, "فایل حذف شد.")
            return redirect("members_portal:documents")

        if remove_field and remove_field.startswith("birth_page:"):
            page_pk = remove_field.split(":", 1)[1]
            MemberBirthCertificatePage.objects.filter(pk=page_pk, member=member).delete()
            messages.success(request, "تصویر حذف شد.")
            return redirect("members_portal:documents")

        form = MemberDocumentsForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            # پاک‌کردن دلیل رد برای هر مدرکی که فایل جدید برایش ارسال شده
            rejection_field_map = {
                "legal_decree_file": "legal_decree_rejection_reason",
                "network_letter_file": "network_letter_rejection_reason",
                "national_id_card_file": "national_id_rejection_reason",
            }
            for file_field, rejection_field in rejection_field_map.items():
                if file_field in request.FILES:
                    setattr(member, rejection_field, "")
            if request.FILES.getlist("birth_certificate_images"):
                member.birth_certificate_rejection_reason = ""

            form.save()
            for image in form.cleaned_data.get("birth_certificate_images") or []:
                MemberBirthCertificatePage.objects.create(member=member, image=image)
            messages.success(request, "مدارک با موفقیت ارسال شد.")
            return redirect("members_portal:documents")
    else:
        form = MemberDocumentsForm(instance=member)

    birth_certificate_pages = member.birth_certificate_pages.all()


    return render(request, "members/documents.html", {
        "form": form, "member": member, "birth_certificate_pages": birth_certificate_pages,
    })


@login_required
def removal_proposal_create_view(request, member_pk):
    if not (request.user.is_staff or request.user.is_superuser or is_board_member(request.user)):
        raise PermissionDenied("شما مجوز پیشنهاد حذف عضو را ندارید.")
    member = get_object_or_404(Member, pk=member_pk)

    if request.method == "POST":
        form = MemberRemovalProposalForm(request.POST)
        if form.is_valid():
            try:
                propose_member_removal(
                    member=member, proposed_by=request.user,
                    reason=form.cleaned_data["reason"], reason_detail=form.cleaned_data["reason_detail"],
                )
                messages.success(request, "پیشنهاد شما ثبت شد و برای تصمیم‌گیری ارسال شد.")
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
            return redirect("members_portal:member_detail", pk=member.pk)
    else:
        form = MemberRemovalProposalForm()

    return render(request, "members/removal_proposal_form.html", {"form": form, "member": member})


@login_required
def removal_proposal_list_view(request):
    if not (request.user.is_staff or request.user.is_superuser or is_board_member(request.user)):
        raise PermissionDenied("شما مجوز مشاهده‌ی این فهرست را ندارید.")

    proposals = MemberRemovalProposal.objects.select_related("member__user", "proposed_by").order_by("-created_at")
    if not (request.user.is_staff or request.user.is_superuser):
        scoped_members = selectors._members_queryset_for(request.user)
        proposals = proposals.filter(member__in=scoped_members)

    return render(request, "members/removal_proposal_list.html", {
        "proposals": proposals,
        "can_decide": request.user.is_staff or request.user.is_superuser or is_board_leadership(request.user),
    })


@login_required
def removal_proposal_approve_view(request, pk):
    proposal = get_object_or_404(MemberRemovalProposal, pk=pk)
    if request.method == "POST":
        form = RemovalDecisionForm(request.POST)
        if form.is_valid():
            try:
                approve_member_removal(proposal=proposal, actor=request.user, note=form.cleaned_data["note"])
                messages.success(request, "پیشنهاد تأیید و عضویت لغو شد.")
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
            return redirect("members_portal:removal_proposals")
    else:
        form = RemovalDecisionForm()
    return render(request, "members/removal_decision_form.html",
                  {"form": form, "proposal": proposal, "action": "تأیید"})


@login_required
def removal_proposal_reject_view(request, pk):
    proposal = get_object_or_404(MemberRemovalProposal, pk=pk)
    if request.method == "POST":
        form = RemovalDecisionForm(request.POST)
        if form.is_valid():
            try:
                reject_member_removal(proposal=proposal, actor=request.user, note=form.cleaned_data["note"])
                messages.success(request, "پیشنهاد رد شد.")
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
            return redirect("members_portal:removal_proposals")
    else:
        form = RemovalDecisionForm()
    return render(request, "members/removal_decision_form.html", {"form": form, "proposal": proposal, "action": "رد"})


@login_required
def member_search_suggestions_view(request):
    """Endpoint سبک JSON برای پیشنهاد زنده — فقط اگر حداقل ۲ حرف تایپ شده باشد."""
    from django.http import JsonResponse

    from .permissions import can_manage_members

    if not can_manage_members(request.user) and not Authorization.has_permission_code(request.user, "member.view"):
        raise PermissionDenied("شما مجوز این عملیات را ندارید.")

    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"results": []})

    members = selectors._members_queryset_for(request.user).select_related("user").filter(
        models.Q(user__first_name__icontains=query)
        | models.Q(user__last_name__icontains=query)
        | models.Q(user__username__icontains=query)
    )[:15]

    results = [
        {
            "pk": m.pk,
            "name": m.user.get_full_name() or m.user.username,
            "national_code": m.user.username,
        }
        for m in members
    ]
    return JsonResponse({"results": results})





@login_required
def forced_password_change_view(request):
    from django.contrib.auth import update_session_auth_hash

    if request.method == "POST":
        form = ForcedPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            request.user.must_change_password = False
            request.user.save(update_fields=["must_change_password"])
            update_session_auth_hash(request, request.user)
            messages.success(request, "رمز عبور شما با موفقیت تغییر کرد.")
            return redirect("members_portal:dashboard")
    else:
        form = ForcedPasswordChangeForm(request.user)

    return render(request, "members/forced_password_change.html", {"form": form})

@login_required
def bale_link_start_view(request):
    from django.conf import settings

    from apps.accounts.bale_services import generate_link_code

    code = generate_link_code(request.user)
    bot_username = settings.BALE_BOT_USERNAME
    bot_link = f"https://ble.ir/{bot_username}"

    return render(request, "members/bale_link.html", {
        "code": code, "bot_link": bot_link, "bot_username": bot_username,
    })

@login_required
def bale_fee_payment_view(request, fee_pk):
    if request.method != "POST":
        raise PermissionDenied("این عملیات فقط از طریق POST مجاز است.")

    from django.contrib import messages as django_messages
    from .bale_payments import initiate_fee_payment
    from .models import MembershipFee

    fee = get_object_or_404(MembershipFee, pk=fee_pk)
    if fee.member.user_id != request.user.id:
        raise PermissionDenied("این حق عضویت متعلق به شما نیست.")

    try:
        initiate_fee_payment(fee, request.user)
        django_messages.success(request, "درخواست پرداخت به بله شما ارسال شد — لطفاً بله را باز کنید.")
    except ValueError as exc:
        django_messages.error(request, str(exc))

    return redirect("members_portal:my_fees")

@login_required
def my_fees_view(request):
    try:
        member = request.user.member_profile
    except Member.DoesNotExist:
        member = None

    fees = MembershipFee.objects.filter(member=member).order_by("-due_date") if member else MembershipFee.objects.none()
    return render(request, "members/my_fees.html", {"fees": fees})


@login_required
def member_document_approve_view(request, pk, document_key):
    from .services import approve_single_document

    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        try:
            approve_single_document(member=member, actor=request.user, document_key=document_key)
            messages.success(request, "مدرک تأیید شد.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, str(exc))
    return redirect("members_portal:member_detail", pk=pk)


@login_required
def member_document_reject_view(request, pk, document_key):
    from .services import reject_single_document

    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        reason = request.POST.get("reason", "")
        try:
            reject_single_document(member=member, actor=request.user, document_key=document_key, reason=reason)
            messages.success(request, "مدرک رد شد و برای کاربر قابل ویرایش مجدد است.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, str(exc))
    return redirect("members_portal:member_detail", pk=pk)


@login_required
def member_detail_view(request, pk):
    from .services import get_document_review_rows

    member = get_object_or_404(Member, pk=pk)
    if not _can_access_member(request.user, member):
        raise PermissionDenied("شما مجوز مشاهده‌ی این عضو را ندارید.")

    membership_periods = member.membership_periods.order_by("-start_date")
    employment_history = (
        EmploymentAssignment.objects.for_user(member.user).select_related("health_house").order_by("-start_date")
    )
    fees = member.fees.order_by("-due_date")
    status_history = member.status_history.select_related("actor").all()
    document_rows = get_document_review_rows(member)

    from apps.authorization.secure_links import make_ref

    return render(request, "members/management_detail.html", {
        "member": member,
        "membership_periods": membership_periods,
        "employment_history": employment_history,
        "fees": fees,
        "status_history": status_history,
        "document_rows": document_rows,
        "member_user_ref": make_ref(member.user.pk),
    })


@login_required
def member_documents_view(request):
    from .models import MemberBirthCertificatePage
    from .services import DOCUMENT_CHECK_MAP

    try:
        member = request.user.member_profile
    except Member.DoesNotExist:
        messages.error(request, "برای ارسال مدارک، ابتدا باید پروفایل عضویت داشته باشید.")
        return redirect("members_portal:dashboard")

    locked_file_fields = {
        "legal_decree_file": bool(member.legal_decree_approved_at),
        "network_letter_file": bool(member.network_letter_approved_at),
        "national_id_card_file": bool(member.national_id_approved_at),
    }
    birth_certificate_locked = bool(member.birth_certificate_approved_at)

    if request.method == "POST":
        remove_field = request.POST.get("remove_field")

        if remove_field in locked_file_fields:
            if locked_file_fields[remove_field]:
                messages.error(request, "این مدرک قبلاً تأیید شده و قابل حذف نیست.")
                return redirect("members_portal:documents")
            getattr(member, remove_field).delete(save=False)
            setattr(member, remove_field, None)
            member.save(update_fields=[remove_field, "updated_at"])
            messages.success(request, "فایل حذف شد.")
            return redirect("members_portal:documents")

        if remove_field and remove_field.startswith("birth_page:"):
            if birth_certificate_locked:
                messages.error(request, "تصاویر شناسنامه قبلاً تأیید شده‌اند و قابل حذف نیستند.")
                return redirect("members_portal:documents")
            page_pk = remove_field.split(":", 1)[1]
            MemberBirthCertificatePage.objects.filter(pk=page_pk, member=member).delete()
            messages.success(request, "تصویر حذف شد.")
            return redirect("members_portal:documents")

        # جلوگیری از تغییر مدارک تأییدشده حتی از طریق ارسال فایل جدید
        for field_name, is_locked in locked_file_fields.items():
            if is_locked and field_name in request.FILES:
                messages.error(request, "برخی از مدارکی که ارسال کرده‌اید قبلاً تأیید شده‌اند و قابل تغییر نیستند.")
                return redirect("members_portal:documents")
        if birth_certificate_locked and request.FILES.getlist("birth_certificate_images"):
            messages.error(request, "تصاویر شناسنامه قبلاً تأیید شده‌اند و قابل تغییر نیستند.")
            return redirect("members_portal:documents")

        form = MemberDocumentsForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            form.save()
            for image in form.cleaned_data.get("birth_certificate_images") or []:
                MemberBirthCertificatePage.objects.create(member=member, image=image)
            messages.success(request, "مدارک با موفقیت ارسال شد.")
            return redirect("members_portal:documents")
    else:
        form = MemberDocumentsForm(instance=member)

    birth_certificate_pages = member.birth_certificate_pages.all()

    return render(request, "members/documents.html", {
        "form": form, "member": member, "birth_certificate_pages": birth_certificate_pages,
        "locked_file_fields": locked_file_fields, "birth_certificate_locked": birth_certificate_locked,
    })