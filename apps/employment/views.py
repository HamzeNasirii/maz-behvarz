from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.authorization.services import Authorization

from . import selectors
from .forms import EmploymentAssignmentCreateForm, EmploymentAssignmentEndForm
from .models import EmploymentAssignment
from .services import create_employment_assignment, end_employment_assignment


@login_required
def employment_list_view(request):
    """
    لیست مدیریتی — فقط Assignmentهایی که در محدوده‌ی دسترسی کاربر
    فعلی (از طریق RoleAssignment/AccessScope) قرار دارند نمایش داده
    می‌شوند. Scope-aware بودن از طریق Authorization.scope_queryset
    در selectors.py تضمین شده است.
    """
    if not Authorization.has_permission_code(request.user, "employment.view"):
        raise PermissionDenied("شما مجوز مشاهده‌ی این فهرست را ندارید.")

    assignments = selectors.current_employees(user=request.user)
    return render(request, "employment/management_list.html", {"assignments": assignments})


@login_required
def employment_detail_view(request, pk):
    assignment = get_object_or_404(EmploymentAssignment, pk=pk)

    if not Authorization.can(request.user, "employment.view", assignment):
        raise PermissionDenied("شما مجوز مشاهده‌ی این رکورد را ندارید.")

    return render(request, "employment/management_detail.html", {"assignment": assignment})


@login_required
def employment_create_view(request):
    if not Authorization.has_permission_code(request.user, "employment.create"):
        raise PermissionDenied("شما مجوز ایجاد تخصیص محل خدمت را ندارید.")

    if request.method == "POST":
        form = EmploymentAssignmentCreateForm(request.POST)
        if form.is_valid():
            create_employment_assignment(
                created_by=request.user,
                user=form.cleaned_data["user"],
                health_house=form.cleaned_data["health_house"],
                employment_type=form.cleaned_data["employment_type"],
                start_date=form.cleaned_data["start_date"],
                is_primary=form.cleaned_data["is_primary"],
                reason=form.cleaned_data["reason"],
            )
            messages.success(request, "تخصیص محل خدمت با موفقیت ثبت شد.")
            return redirect("employment:list")
    else:
        form = EmploymentAssignmentCreateForm()

    return render(request, "employment/management_create.html", {"form": form})


@login_required
def employment_end_view(request, pk):
    assignment = get_object_or_404(EmploymentAssignment, pk=pk)

    if not Authorization.can(request.user, "employment.update", assignment):
        raise PermissionDenied("شما مجوز پایان‌دادن به این تخصیص را ندارید.")

    if request.method == "POST":
        form = EmploymentAssignmentEndForm(request.POST)
        if form.is_valid():
            end_employment_assignment(
                assignment=assignment,
                ended_by=request.user,
                end_date=form.cleaned_data["end_date"],
                reason=form.cleaned_data["reason"],
            )
            messages.success(request, "تخصیص محل خدمت پایان یافت.")
            return redirect("employment:detail", pk=assignment.pk)
    else:
        form = EmploymentAssignmentEndForm()

    return render(request, "employment/management_end.html", {"form": form, "assignment": assignment})