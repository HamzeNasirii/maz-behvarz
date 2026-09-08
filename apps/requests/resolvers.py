from apps.authorization.choices import AccessScopeType


def request_health_houses(request_obj):
    """
    اگر Request هیچ Scope نداشته باشد (مثلاً یک PROFILE_UPDATE شخصی)،
    Scope-aware نیست و هیچ محدودیتی اعمال نمی‌شود — طبق الگوی Document
    (فاز ۳۲): بازگشت None یعنی بدون محدودیت.
    """
    if request_obj.scope_id is None:
        return None
    return request_obj.scope.get_health_house_queryset()


def scope_request_queryset(queryset, house_ids):
    """Python-side iteration — همان الگوی شناخته‌شده‌ی Committee/Document/RoleAssignment."""
    house_ids_set = set(house_ids)
    matching_ids = []
    for req in queryset.select_related("scope"):
        if req.scope_id is None:
            matching_ids.append(req.pk)
            continue
        if req.scope.scope_type == AccessScopeType.GLOBAL:
            matching_ids.append(req.pk)
            continue
        req_houses = set(req.scope.get_health_house_queryset().values_list("pk", flat=True))
        if req_houses & house_ids_set:
            matching_ids.append(req.pk)
    return queryset.filter(pk__in=matching_ids)