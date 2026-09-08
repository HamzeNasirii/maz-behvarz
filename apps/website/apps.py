from django.apps import AppConfig


class WebsiteConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.website"

    def ready(self):
        from apps.authorization.registry import register_health_house_resolver, register_queryset_scope_resolver

        from .models import MembershipApplication
        from .resolvers import membership_application_health_houses, scope_membership_application_queryset

        register_health_house_resolver(MembershipApplication, membership_application_health_houses)
        register_queryset_scope_resolver(MembershipApplication, scope_membership_application_queryset)