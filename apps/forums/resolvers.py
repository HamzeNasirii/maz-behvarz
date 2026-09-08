def forum_health_houses(forum):
    return forum.scope.get_health_house_queryset()


def scope_forum_queryset(queryset, house_ids):
    house_ids_set = set(house_ids)
    matching_ids = []
    for f in queryset.select_related("scope"):
        f_houses = set(f.scope.get_health_house_queryset().values_list("pk", flat=True))
        if f_houses & house_ids_set:
            matching_ids.append(f.pk)
    return queryset.filter(pk__in=matching_ids)