from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from . import selectors
from .forms import RoleAssignmentCreateForm, RoleAssignmentOptionalReasonForm, RoleAssignmentReasonForm
from .models import RoleAssignment
from .role_lifecycle_services import (
    approve_role_assignment_lifecycle,
    assign_role,
    cancel_role_assignment,
    end_role_assignment,
    reactivate_role_assignment,
    reject_role_assignment_lifecycle,
    revoke_role_assignment,
    submit_role_assignment_for_approval,
    suspend_role_assignment,
)
from .services import Authorization


@login_required
def portal_role_history_view(request):
    """
    مالکیت از طریق request.user تضمین شده — نیازی به عبور از
    Authorization Engine نیست (فقط اطلاعات خود کاربر).
    """
    assignments = selectors.role_assignment_history(request.user)
    return render(request, "authorization/portal_roles.html", {"assignments": assignments})


@login_required
def management_list_view(request):
    from .secure_links import resolve_ref

    if not Authorization.has_permission_code(request.user, "role.view"):
        raise PermissionDenied("شما مجوز مشاهده‌ی این فهرست را ندارید.")

    ref = request.GET.get("ref")
    target_user_id = resolve_ref(ref)
    target_user = None
    if target_user_id:
        from django.contrib.auth import get_user_model
        target_user = get_user_model().objects.filter(pk=target_user_id).first()

    assignments = Authorization.scope_queryset(
        request.user, RoleAssignment.objects.select_related("user", "role", "access_scope")
    )
    if target_user:
        assignments = assignments.filter(user_id=target_user.pk)

    create_form = None
    if target_user and Authorization.has_permission_code(request.user, "role.assign"):
        if request.method == "POST":
            create_form = RoleAssignmentCreateForm(request.POST)
            if create_form.is_valid():
                try:
                    assign_role(assigned_by=request.user, **create_form.cleaned_data)
                    messages.success(request, "تخصیص نقش پیشنهادی ثبت شد.")
                    return redirect(f"{request.path}?ref={ref}")
                except (PermissionDenied, ValidationError) as exc:
                    messages.error(request, str(exc))
        else:
            create_form = RoleAssignmentCreateForm(initial={"user": target_user.pk})

    return render(request, "authorization/management_list.html", {
        "assignments": assignments,
        "target_user": target_user,
        "ref": ref,
        "create_form": create_form,
    })


@login_required
def management_detail_view(request, pk):
    assignment = get_object_or_404(RoleAssignment, pk=pk)
    if not (request.user.is_staff or Authorization.can(request.user, "role.view", assignment)):
        raise PermissionDenied("شما مجوز مشاهده‌ی این تخصیص نقش را ندارید.")
    history = assignment.status_history.select_related("actor").all()
    return render(request, "authorization/management_detail.html", {"assignment": assignment, "history": history})

@login_required
def management_create_view(request):
    from .secure_links import resolve_ref

    if not Authorization.has_permission_code(request.user, "role.assign"):
        raise PermissionDenied("شما مجوز تخصیص نقش را ندارید.")

    target_user = None
    ref = request.GET.get("ref") or request.POST.get("ref")
    target_user_id = resolve_ref(ref)
    if target_user_id:
        from django.contrib.auth import get_user_model
        target_user = get_user_model().objects.filter(pk=target_user_id).first()

    if request.method == "POST":
        form = RoleAssignmentCreateForm(request.POST)
        if form.is_valid():
            try:
                assignment = assign_role(assigned_by=request.user, **form.cleaned_data)
                messages.success(request, "تخصیص نقش پیشنهادی ثبت شد.")
                return redirect("roles:management_detail", pk=assignment.pk)
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
    else:
        initial = {}
        if target_user:
            initial["user"] = target_user.pk
        form = RoleAssignmentCreateForm(initial=initial)

    return render(request, "authorization/management_create.html", {
        "form": form, "target_user": target_user, "ref": ref,
    })


def _handle_transition(request, pk, transition_func, requires_reason, success_message):
    assignment = get_object_or_404(RoleAssignment, pk=pk)
    if request.method == "POST":
        form = RoleAssignmentReasonForm(request.POST) if requires_reason else RoleAssignmentOptionalReasonForm(request.POST)
        if form.is_valid():
            try:
                transition_func(assignment=assignment, actor=request.user, reason=form.cleaned_data.get("reason", ""))
                messages.success(request, success_message)
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
            return redirect("roles:management_detail", pk=assignment.pk)
    else:
        form = RoleAssignmentReasonForm() if requires_reason else RoleAssignmentOptionalReasonForm()
    return render(request, "authorization/transition_form.html", {"form": form, "assignment": assignment})


@login_required
def submit_view(request, pk):
    assignment = get_object_or_404(RoleAssignment, pk=pk)
    try:
        submit_role_assignment_for_approval(assignment=assignment, actor=request.user)
        messages.success(request, "برای بررسی ارسال شد.")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
    return redirect("roles:management_detail", pk=assignment.pk)


@login_required
def approve_view(request, pk):
    assignment = get_object_or_404(RoleAssignment, pk=pk)
    try:
        approve_role_assignment_lifecycle(assignment=assignment, actor=request.user)
        messages.success(request, "تخصیص نقش تأیید و فعال شد.")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
    return redirect("roles:management_detail", pk=assignment.pk)


@login_required
def reject_view(request, pk):
    return _handle_transition(request, pk, reject_role_assignment_lifecycle, True, "تخصیص نقش رد شد.")


@login_required
def suspend_view(request, pk):
    return _handle_transition(request, pk, suspend_role_assignment, True, "تخصیص نقش معلق شد.")


@login_required
def reactivate_view(request, pk):
    return _handle_transition(request, pk, reactivate_role_assignment, False, "تخصیص نقش دوباره فعال شد.")


@login_required
def end_view(request, pk):
    from django.utils import timezone as tz

    assignment = get_object_or_404(RoleAssignment, pk=pk)
    try:
        end_role_assignment(assignment=assignment, actor=request.user, end_date=tz.localdate())
        messages.success(request, "تخصیص نقش پایان یافت.")
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
    return redirect("roles:management_detail", pk=assignment.pk)


@login_required
def revoke_view(request, pk):
    return _handle_transition(request, pk, revoke_role_assignment, True, "تخصیص نقش به‌صورت اجباری لغو شد.")


@login_required
def cancel_view(request, pk):
    return _handle_transition(request, pk, cancel_role_assignment, False, "پیشنهاد تخصیص نقش لغو شد.")