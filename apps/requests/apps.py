from django.apps import AppConfig


class RequestsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.requests"
    verbose_name = "درخواست‌ها و گردش‌کار"

    def ready(self):
        from apps.authorization.registry import (
            register_health_house_resolver,
            register_queryset_scope_resolver,
        )

        from .models import Request
        from .resolvers import request_health_houses, scope_request_queryset

        register_health_house_resolver(Request, request_health_houses)
        register_queryset_scope_resolver(Request, scope_request_queryset)