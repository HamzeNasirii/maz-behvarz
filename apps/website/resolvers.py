def membership_application_health_houses(application):
    from apps.organization.models import HealthHouse

    if not application.health_house_id:
        return None
    return HealthHouse.objects.filter(pk=application.health_house_id)


def scope_membership_application_queryset(queryset, house_ids):
    return queryset.filter(health_house_id__in=house_ids)