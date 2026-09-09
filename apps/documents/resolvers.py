from apps.authorization.choices import AccessScopeType


def document_health_houses(document):
    """
    اگر سند Scope نداشته باشد، Scope-aware نیست (طبق الگوی Resolverهای
    موجود: بازگشت None یعنی هیچ محدودیت Scope‌ای اعمال نمی‌شود).
    """
    if document.scope_id is None:
        return None
    return document.scope.get_health_house_queryset()


def scope_document_queryset(queryset, house_ids):
    """
    Python-side iteration — مشابه الگوی apps.committees (Technical
    Debt مستند‌شده در فازهای قبل)، چون Document.scope یک AccessScope
    تک‌سطحی است و رابطه‌ی مستقیم دیتابیسی به HealthHouse ندارد.
    """
    house_ids_set = set(house_ids)
    matching_ids = []
    for doc in queryset.select_related("scope"):
        if doc.scope_id is None:
            matching_ids.append(doc.pk)
            continue
        if doc.scope.scope_type == AccessScopeType.GLOBAL:
            matching_ids.append(doc.pk)
            continue
        doc_houses = set(doc.scope.get_health_house_queryset().values_list("pk", flat=True))
        if doc_houses & house_ids_set:
            matching_ids.append(doc.pk)
    return queryset.filter(pk__in=matching_ids)