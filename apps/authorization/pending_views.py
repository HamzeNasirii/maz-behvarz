from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from .admin_dashboard import _can_view_pending_dashboard
from .choices import ApprovalStatus
from .pending_forms import RejectReasonForm
from .services import Authorization


def _require_access(user):
    if not _can_view_pending_dashboard(user):
        raise PermissionDenied("شما مجوز مشاهده‌ی این صفحه را ندارید.")


@login_required
def pending_applications_view(request):
    from apps.website.models import MembershipApplication
    from apps.website.services import approve_membership_application, reject_membership_application

    _require_access(request.user)
    applications = Authorization.scope_queryset(
        request.user,
        MembershipApplication.objects.filter(status=ApprovalStatus.PENDING).select_related("health_house"),
    )

    if request.method == "POST":
        app_obj = get_object_or_404(MembershipApplication, pk=request.POST.get("item_id"))
        if not Authorization.can(request.user, "member.approve", app_obj):
            raise PermissionDenied("شما مجوز رسیدگی به این درخواست را ندارید.")
        action = request.POST.get("action")
        try:
            if action == "approve":
                approve_membership_application(application=app_obj, approved_by=request.user)
                messages.success(request, "درخواست عضویت تأیید و عضو ساخته شد.")
            elif action == "reject":
                form = RejectReasonForm(request.POST)
                if form.is_valid():
                    reject_membership_application(
                        application=app_obj, rejected_by=request.user, note=form.cleaned_data["reason"],
                    )
                    messages.success(request, "درخواست عضویت رد شد.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, str(exc))
        return redirect("pending_mgmt:applications")

    return render(request, "authorization/pending_applications.html", {
        "applications": applications, "reject_form": RejectReasonForm(),
    })


@login_required
def pending_members_view(request):
    from apps.members.models import Member
    from apps.members.services import approve_member, reject_member

    _require_access(request.user)
    members = Member.objects.for_user(request.user).filter(
        approval_status=ApprovalStatus.PENDING
    ).select_related("user")

    if request.method == "POST":
        member = get_object_or_404(Member, pk=request.POST.get("item_id"))
        if not Authorization.can(request.user, "member.approve", member):
            raise PermissionDenied("شما مجوز رسیدگی به این عضو را ندارید.")
        action = request.POST.get("action")
        try:
            if action == "approve":
                approve_member(member=member, approved_by=request.user)
                messages.success(request, "عضویت تأیید شد.")
            elif action == "reject":
                form = RejectReasonForm(request.POST)
                if form.is_valid():
                    reject_member(member=member, rejected_by=request.user, reason=form.cleaned_data["reason"])
                    messages.success(request, "عضویت رد شد.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, str(exc))
        return redirect("pending_mgmt:members")

    return render(request, "authorization/pending_members.html", {
        "members": members, "reject_form": RejectReasonForm(),
    })


@login_required
def pending_employment_view(request):
    from apps.employment.models import EmploymentAssignment
    from apps.employment.services import approve_employment_transfer, reject_employment_transfer

    _require_access(request.user)
    assignments = EmploymentAssignment.objects.for_user(request.user).filter(
        approval_status=ApprovalStatus.PENDING
    ).select_related("user", "health_house")

    if request.method == "POST":
        assignment = get_object_or_404(EmploymentAssignment, pk=request.POST.get("item_id"))
        if not Authorization.can(request.user, "employment.approve", assignment):
            raise PermissionDenied("شما مجوز رسیدگی به این جابه‌جایی را ندارید.")
        action = request.POST.get("action")
        try:
            if action == "approve":
                approve_employment_transfer(assignment=assignment, approved_by=request.user)
                messages.success(request, "جابه‌جایی محل خدمت تأیید شد.")
            elif action == "reject":
                form = RejectReasonForm(request.POST)
                if form.is_valid():
                    reject_employment_transfer(
                        assignment=assignment, rejected_by=request.user, reason=form.cleaned_data["reason"],
                    )
                    messages.success(request, "جابه‌جایی محل خدمت رد شد.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, str(exc))
        return redirect("pending_mgmt:employment")

    return render(request, "authorization/pending_employment.html", {
        "assignments": assignments, "reject_form": RejectReasonForm(),
    })


@login_required
def pending_roles_view(request):
    from .models import RoleAssignment
    from .role_services import approve_role_assignment, reject_role_assignment

    _require_access(request.user)
    assignments = Authorization.scope_queryset(
        request.user,
        RoleAssignment.objects.filter(approval_status=ApprovalStatus.PENDING).select_related(
            "user", "role", "access_scope"
        ),
    )

    if request.method == "POST":
        assignment = get_object_or_404(RoleAssignment, pk=request.POST.get("item_id"))
        if not Authorization.can(request.user, "role.approve", assignment):
            raise PermissionDenied("شما مجوز رسیدگی به این تخصیص نقش را ندارید.")
        action = request.POST.get("action")
        try:
            if action == "approve":
                approve_role_assignment(role_assignment=assignment, approved_by=request.user)
                messages.success(request, "تخصیص نقش تأیید شد.")
            elif action == "reject":
                form = RejectReasonForm(request.POST)
                if form.is_valid():
                    reject_role_assignment(
                        role_assignment=assignment, rejected_by=request.user, reason=form.cleaned_data["reason"],
                    )
                    messages.success(request, "تخصیص نقش رد شد.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, str(exc))
        return redirect("pending_mgmt:roles")

    return render(request, "authorization/pending_roles.html", {
        "assignments": assignments, "reject_form": RejectReasonForm(),
    })