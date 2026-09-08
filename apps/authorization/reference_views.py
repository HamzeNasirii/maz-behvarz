from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.board.permissions import is_board_leadership

from .models import AccessScope, Permission, Role
from .reference_forms import AccessScopeForm, PermissionForm, RoleForm


def _require_access(user):
    if not (user.is_superuser or user.is_staff or is_board_leadership(user)):
        raise PermissionDenied("شما مجوز مدیریت این بخش را ندارید.")


# --- Role ---

@login_required
def role_list_view(request):
    _require_access(request.user)
    roles = Role.objects.all().order_by("code")
    return render(request, "authorization/role_list.html", {"roles": roles})


@login_required
def role_create_view(request):
    _require_access(request.user)
    if request.method == "POST":
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "نقش با موفقیت ایجاد شد.")
            return redirect("auth_ref:role_list")
    else:
        form = RoleForm()
    return render(request, "authorization/reference_form.html", {"form": form, "title": "ایجاد نقش جدید"})


@login_required
def role_edit_view(request, pk):
    _require_access(request.user)
    role = get_object_or_404(Role, pk=pk)
    if request.method == "POST":
        form = RoleForm(request.POST, instance=role, editor=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "نقش ویرایش شد.")
            return redirect("auth_ref:role_list")
    else:
        form = RoleForm(instance=role, editor=request.user)

    permission_descriptions = {p.pk: p.description for p in Permission.objects.all()}

    return render(request, "authorization/role_edit_form.html", {
        "form": form, "role": role, "permission_descriptions": permission_descriptions,
    })


@login_required
def role_toggle_view(request, pk):
    _require_access(request.user)
    role = get_object_or_404(Role, pk=pk)
    if request.method == "POST":
        role.is_active = not role.is_active
        role.save(update_fields=["is_active"])
        messages.success(request, "وضعیت نقش تغییر کرد.")
    return redirect("auth_ref:role_list")


# --- Permission ---

@login_required
def permission_list_view(request):
    _require_access(request.user)
    permissions = Permission.objects.all().order_by("code")
    return render(request, "authorization/permission_list.html", {"permissions": permissions})


@login_required
def permission_create_view(request):
    _require_access(request.user)
    if request.method == "POST":
        form = PermissionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "مجوز با موفقیت ایجاد شد.")
            return redirect("auth_ref:permission_list")
    else:
        form = PermissionForm()
    return render(request, "authorization/reference_form.html", {"form": form, "title": "ایجاد مجوز جدید"})


@login_required
def permission_edit_view(request, pk):
    _require_access(request.user)
    permission = get_object_or_404(Permission, pk=pk)
    if request.method == "POST":
        form = PermissionForm(request.POST, instance=permission)
        if form.is_valid():
            form.save()
            messages.success(request, "مجوز ویرایش شد.")
            return redirect("auth_ref:permission_list")
    else:
        form = PermissionForm(instance=permission)
    return render(request, "authorization/reference_form.html", {"form": form, "title": f"ویرایش مجوز «{permission.code}»"})


# --- AccessScope ---

@login_required
def scope_list_view(request):
    _require_access(request.user)
    scopes = AccessScope.objects.select_related("province", "county", "network", "center", "house", "committee").all()
    return render(request, "authorization/scope_list.html", {"scopes": scopes})

@login_required
def scope_list_view(request):
    _require_access(request.user)
    scopes = AccessScope.objects.select_related("province", "county", "network", "center", "house", "committee").all()

    from .scope_helpers import get_access_scope_province_id, get_accessible_province_ids

    accessible_province_ids = get_accessible_province_ids(request.user)
    if accessible_province_ids is not None:
        allowed_ids = [
            s.pk for s in scopes
            if get_access_scope_province_id(s) in accessible_province_ids
        ]
        scopes = scopes.filter(pk__in=allowed_ids)

    return render(request, "authorization/scope_list.html", {"scopes": scopes})


@login_required
def scope_create_view(request):
    _require_access(request.user)

    from .scope_helpers import get_access_scope_province_id, get_accessible_province_ids

    accessible_province_ids = get_accessible_province_ids(request.user)

    if request.method == "POST":
        form = AccessScopeForm(request.POST)
        if form.is_valid():
            new_scope = form.save(commit=False)
            if accessible_province_ids is not None:
                scope_province_id = get_access_scope_province_id(new_scope)
                if scope_province_id not in accessible_province_ids:
                    raise PermissionDenied("شما فقط می‌توانید محدوده‌ی دسترسی برای استان خودتان ایجاد کنید.")
            new_scope.save()
            messages.success(request, "محدوده‌ی دسترسی با موفقیت ایجاد شد.")
            return redirect("auth_ref:scope_list")
    else:
        form = AccessScopeForm()
    return render(request, "authorization/reference_form.html", {"form": form, "title": "ایجاد محدوده‌ی دسترسی جدید"})