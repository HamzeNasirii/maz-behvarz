from django.apps import AppConfig


class ForumsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.forums"
    verbose_name = "فروم‌ها"

    def ready(self):
        from apps.authorization.registry import register_health_house_resolver, register_queryset_scope_resolver
        from .models import Forum
        from .resolvers import forum_health_houses, scope_forum_queryset

        register_health_house_resolver(Forum, forum_health_houses)
        register_queryset_scope_resolver(Forum, scope_forum_queryset)