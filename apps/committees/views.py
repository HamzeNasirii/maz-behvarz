from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import selectors
from .authorization import can_manage_committee
from .forms import (
    CommitteeCreateForm,
    CommitteeMembershipCreateForm,
    CommitteeMembershipEndForm,
    CommitteeOptionalReasonForm,
    CommitteeReasonForm,
)
from .models import Committee, CommitteeMembership
from .services import (
    activate_committee,
    add_committee_member,
    archive_committee,
    create_committee,
    end_committee,
    remove_committee_member,
    suspend_committee,
)


@login_required
def management_list_view(request):
    from .authorization import committees_for_user

    committees = committees_for_user(request.user)
    return render(request, "committees/management_list.html", {"committees": committees})


@login_required
def management_detail_view(request, pk):
    committee = get_object_or_404(Committee, pk=pk)
    if not can_manage_committee(request.user, committee, "committee.view"):
        raise PermissionDenied("شما مجوز مشاهده‌ی این کمیته را ندارید.")

    members = selectors.memberships_for_committee(committee)
    history = selectors.committee_history(request.user, committee)
    return render(request, "committees/management_detail.html", {
        "committee": committee, "members": members, "history": history,
    })


@login_required
def management_create_view(request):
    from apps.authorization.services import Authorization

    if not (request.user.is_superuser or request.user.is_staff
            or Authorization.has_permission_code(request.user, "committee.create")):
        raise PermissionDenied("شما مجوز ایجاد کمیته را ندارید.")

    if request.method == "POST":
        form = CommitteeCreateForm(request.POST)
        if form.is_valid():
            committee = create_committee(created_by=request.user, **form.cleaned_data)
            messages.success(request, "کمیته ایجاد شد.")
            return redirect("committees_mgmt:detail", pk=committee.pk)
    else:
        form = CommitteeCreateForm()
    return render(request, "committees/management_create.html", {"form": form})


def _handle_committee_transition(request, pk, transition_func, requires_reason, success_message):
    committee = get_object_or_404(Committee, pk=pk)
    if request.method == "POST":
        form = CommitteeReasonForm(request.POST) if requires_reason else CommitteeOptionalReasonForm(request.POST)
        if form.is_valid():
            try:
                transition_func(committee=committee, actor=request.user, reason=form.cleaned_data.get("reason", ""))
                messages.success(request, success_message)
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
            return redirect("committees_mgmt:detail", pk=committee.pk)
    else:
        form = CommitteeReasonForm() if requires_reason else CommitteeOptionalReasonForm()
    return render(request, "committees/transition_form.html", {"form": form, "committee": committee})


@login_required
def activate_view(request, pk):
    return _handle_committee_transition(request, pk, activate_committee, False, "کمیته فعال شد.")


@login_required
def suspend_view(request, pk):
    return _handle_committee_transition(request, pk, suspend_committee, True, "کمیته معلق شد.")


@login_required
def end_view(request, pk):
    return _handle_committee_transition(request, pk, end_committee, False, "کمیته پایان یافت.")


@login_required
def archive_view(request, pk):
    return _handle_committee_transition(request, pk, archive_committee, False, "کمیته بایگانی شد.")


@login_required
def member_add_view(request, pk):
    committee = get_object_or_404(Committee, pk=pk)
    if not can_manage_committee(request.user, committee, "committee.manage_members"):
        raise PermissionDenied("شما مجوز افزودن عضو به این کمیته را ندارید.")

    if request.method == "POST":
        form = CommitteeMembershipCreateForm(request.POST)
        if form.is_valid():
            try:
                add_committee_member(
                    committee=committee, added_by=request.user,
                    user=form.cleaned_data["user"], start_date=form.cleaned_data["start_date"],
                    reason=form.cleaned_data["reason"],
                )
                messages.success(request, "عضو با موفقیت اضافه شد.")
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
            return redirect("committees_mgmt:detail", pk=committee.pk)
    else:
        form = CommitteeMembershipCreateForm()
    return render(request, "committees/member_add.html", {"form": form, "committee": committee})


@login_required
def member_remove_view(request, membership_pk):
    membership = get_object_or_404(CommitteeMembership, pk=membership_pk)
    if not can_manage_committee(request.user, membership.committee, "committee.manage_members"):
        raise PermissionDenied("شما مجوز حذف این عضو را ندارید.")

    if request.method == "POST":
        form = CommitteeMembershipEndForm(request.POST)
        if form.is_valid():
            remove_committee_member(
                membership=membership, removed_by=request.user,
                end_date=form.cleaned_data["end_date"], reason=form.cleaned_data["reason"],
            )
            messages.success(request, "عضویت پایان یافت.")
            return redirect("committees_mgmt:detail", pk=membership.committee.pk)
    else:
        form = CommitteeMembershipEndForm(initial={"end_date": timezone.localdate()})
    return render(request, "committees/member_remove.html", {"form": form, "membership": membership})