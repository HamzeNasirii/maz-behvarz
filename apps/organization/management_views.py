from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    CenterCreateForm, CenterEditForm,
    CountyCreateForm, CountyEditForm,
    HouseCreateForm, HouseEditForm,
    NetworkCreateForm, NetworkEditForm,
    ProvinceForm,
)
from .models import County, HealthCenter, HealthHouse, HealthNetwork, Province
from .permissions import can_manage_organization

LEVELS = {
    "province": {
        "model": Province, "create_form": ProvinceForm, "edit_form": ProvinceForm,
        "label": "استان", "parent_field": None,
    },
    "county": {
        "model": County, "create_form": CountyCreateForm, "edit_form": CountyEditForm,
        "label": "شهرستان", "parent_field": "province",
    },
    "network": {
        "model": HealthNetwork, "create_form": NetworkCreateForm, "edit_form": NetworkEditForm,
        "label": "شبکه بهداشت و درمان", "parent_field": "county",
    },
    "center": {
        "model": HealthCenter, "create_form": CenterCreateForm, "edit_form": CenterEditForm,
        "label": "مرکز خدمات جامع سلامت", "parent_field": "network",
    },
    "house": {
        "model": HealthHouse, "create_form": HouseCreateForm, "edit_form": HouseEditForm,
        "label": "خانه بهداشت", "parent_field": "center",
    },
}

LEVEL_ORDER = ["province", "county", "network", "center", "house"]

CHILD_RELATION = {
    "province": "counties",
    "county": "health_networks",
    "network": "health_centers",
    "center": "health_houses",
}


def _level_index(level):
    return LEVEL_ORDER.index(level)


def _children_of(level, parent):
    relation = CHILD_RELATION[level]
    return getattr(parent, relation).all().order_by("name")


def _serialize_node(instance, level):
    return {"pk": instance.pk, "name": instance.name, "is_active": instance.is_active, "level": level}


def _get_ancestors(level, instance):
    """
    زنجیره‌ی والدها از بالا (استان) تا والد مستقیم — برای ساخت
    Breadcrumb در صفحه‌ی جزئیات.
    """
    ancestors = []
    current = instance
    current_level = level
    while LEVELS[current_level]["parent_field"]:
        parent_field = LEVELS[current_level]["parent_field"]
        parent = getattr(current, parent_field)
        parent_level = LEVEL_ORDER[_level_index(current_level) - 1]
        ancestors.insert(0, {"level": parent_level, "pk": parent.pk, "name": parent.name})
        current = parent
        current_level = parent_level
    return ancestors


def _require_access(user):
    if not can_manage_organization(user):
        raise PermissionDenied("شما مجوز مدیریت ساختار سازمانی را ندارید.")


def _accessible_province_ids(user):
    """
    اگر None برگرداند، یعنی کاربر (Staff/Superuser) به همه‌ی استان‌ها
    دسترسی کامل دارد — هیچ فیلتری اعمال نشود. در غیر این صورت، فقط
    شناسه‌ی استان‌هایی که کاربر واقعاً از طریق RoleAssignment(سطح
    استان) به آن‌ها وصل است برگردانده می‌شود — برای جلوگیری از دیدن
    ساختار سایر استان‌ها (حتی توسط رئیس/نایب‌رئیس/دبیر).
    """
    if user.is_superuser or user.is_staff:
        return None

    from apps.authorization.choices import AccessScopeType
    from apps.authorization.services import Authorization

    province_ids = set()
    for assignment in Authorization.get_active_role_assignments(user).select_related("access_scope"):
        scope = assignment.access_scope
        if scope.scope_type == AccessScopeType.PROVINCE and scope.province_id:
            province_ids.add(scope.province_id)
    return province_ids


def _get_province_id_of(level, instance):
    """استخراج شناسه‌ی استان مربوط به یک نمونه از هر سطح سازمانی."""
    if level == "province":
        return instance.pk
    if level == "county":
        return instance.province_id
    if level == "network":
        return instance.county.province_id
    if level == "center":
        return instance.network.county.province_id
    if level == "house":
        return instance.center.network.county.province_id
    return None


def _search_all_levels(query, accessible_province_ids):
    """جستجوی سراسری روی هر ۵ سطح، محدود به استان‌های مجاز کاربر (اگر محدودیتی وجود داشته باشد)."""
    results = []
    for level, config in LEVELS.items():
        matches = config["model"].objects.filter(name__icontains=query).order_by("name")
        for m in matches:
            if accessible_province_ids is not None:
                if _get_province_id_of(level, m) not in accessible_province_ids:
                    continue
            results.append({
                "pk": m.pk, "name": m.name, "level": level,
                "level_label": config["label"], "is_active": m.is_active,
            })
    return results


@login_required
def org_tree_view(request):
    _require_access(request.user)
    accessible_province_ids = _accessible_province_ids(request.user)
    query = request.GET.get("q", "").strip()

    if query:
        results = _search_all_levels(query, accessible_province_ids)
        return render(request, "organization/management_search_results.html", {
            "results": results, "query": query,
        })

    provinces = Province.objects.all().order_by("name")
    if accessible_province_ids is not None:
        provinces = provinces.filter(pk__in=accessible_province_ids)

    items = [_serialize_node(p, "province") for p in provinces]
    return render(request, "organization/management_tree.html", {
        "items": items, "can_add_province": request.user.is_staff or request.user.is_superuser,
    })


@login_required
def org_search_suggestions_view(request):
    """
    Endpoint سبک برای پیشنهاد زنده (Autocomplete) — فقط JSON برمی‌گرداند،
    بدون رندر HTML؛ حداکثر ۱۵ نتیجه، فقط اگر حداقل ۲ حرف تایپ شده باشد.
    """
    from django.http import JsonResponse

    _require_access(request.user)
    accessible_province_ids = _accessible_province_ids(request.user)
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"results": []})
    return JsonResponse({"results": _search_all_levels(query, accessible_province_ids)[:15]})


@login_required
def org_detail_view(request, level, pk):
    _require_access(request.user)
    config = LEVELS.get(level)
    if config is None:
        raise PermissionDenied("سطح نامعتبر است.")

    instance = get_object_or_404(config["model"], pk=pk)

    accessible_province_ids = _accessible_province_ids(request.user)
    if accessible_province_ids is not None:
        if _get_province_id_of(level, instance) not in accessible_province_ids:
            raise PermissionDenied("شما مجوز مشاهده‌ی این بخش از ساختار سازمانی را ندارید.")

    next_level = LEVEL_ORDER[_level_index(level) + 1] if level != "house" else None
    children = []
    if next_level:
        children = [_serialize_node(c, next_level) for c in _children_of(level, instance)]

    return render(request, "organization/management_detail.html", {
        "instance": instance,
        "level": level,
        "level_label": config["label"],
        "children": children,
        "next_level": next_level,
        "next_label": LEVELS[next_level]["label"] if next_level else None,
        "ancestors": _get_ancestors(level, instance),
    })


@login_required
def org_create_view(request, level):
    _require_access(request.user)
    config = LEVELS.get(level)
    if config is None:
        raise PermissionDenied("سطح نامعتبر است.")

    if level == "province" and not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("فقط ادمین می‌تواند استان جدید اضافه کند.")

    parent_id = request.GET.get("parent") or request.POST.get("parent")
    parent_instance = None
    if config["parent_field"] and parent_id:
        parent_level = LEVEL_ORDER[_level_index(level) - 1]
        parent_model = LEVELS[parent_level]["model"]
        parent_instance = get_object_or_404(parent_model, pk=parent_id)

        accessible_province_ids = _accessible_province_ids(request.user)
        if accessible_province_ids is not None:
            if _get_province_id_of(parent_level, parent_instance) not in accessible_province_ids:
                raise PermissionDenied("شما مجوز افزودن زیرمجموعه به این بخش را ندارید.")

    if request.method == "POST":
        form = config["create_form"](request.POST)
        if form.is_valid():
            new_instance = form.save(commit=False)
            if config["parent_field"] and parent_instance:
                setattr(new_instance, config["parent_field"], parent_instance)
            new_instance.save()

            from .scope_sync import ensure_access_scope_for, ensure_forum_for
            new_scope = ensure_access_scope_for(level, new_instance)
            ensure_forum_for(level, new_instance, new_scope)

            messages.success(request, f"{config['label']} با موفقیت ایجاد شد.")
            if config["parent_field"] and parent_id:
                parent_level = LEVEL_ORDER[_level_index(level) - 1]
                return redirect("org_mgmt:detail", level=parent_level, pk=parent_id)
            return redirect("org_mgmt:tree")
    else:
        form = config["create_form"]()

    return render(request, "organization/management_form.html", {
        "form": form, "level_label": config["label"], "mode": "create",
        "parent_id": parent_id, "parent_instance": parent_instance,
    })


@login_required
def org_edit_view(request, level, pk):
    _require_access(request.user)
    config = LEVELS.get(level)
    if config is None:
        raise PermissionDenied("سطح نامعتبر است.")

    instance = get_object_or_404(config["model"], pk=pk)

    accessible_province_ids = _accessible_province_ids(request.user)
    if accessible_province_ids is not None:
        if _get_province_id_of(level, instance) not in accessible_province_ids:
            raise PermissionDenied("شما مجوز ویرایش این بخش از ساختار سازمانی را ندارید.")

    if request.method == "POST":
        form = config["edit_form"](request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f"{config['label']} با موفقیت ویرایش شد.")
            return redirect("org_mgmt:detail", level=level, pk=instance.pk)
    else:
        form = config["edit_form"](instance=instance)

    return render(request, "organization/management_form.html", {
        "form": form, "label_label": config["label"], "level_label": config["label"], "mode": "edit",
    })


@login_required
def org_toggle_active_view(request, level, pk):
    _require_access(request.user)
    config = LEVELS.get(level)
    if config is None:
        raise PermissionDenied("سطح نامعتبر است.")

    instance = get_object_or_404(config["model"], pk=pk)

    accessible_province_ids = _accessible_province_ids(request.user)
    if accessible_province_ids is not None:
        if _get_province_id_of(level, instance) not in accessible_province_ids:
            raise PermissionDenied("شما مجوز تغییر وضعیت این بخش از ساختار سازمانی را ندارید.")

    if request.method == "POST":
        instance.is_active = not instance.is_active
        instance.save(update_fields=["is_active", "updated_at"])
        state = "فعال" if instance.is_active else "غیرفعال"
        messages.success(request, f"{config['label']} «{instance.name}» {state} شد.")
    return redirect("org_mgmt:detail", level=level, pk=instance.pk) if level != "province" else redirect(
        "org_mgmt:tree")