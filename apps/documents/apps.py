from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.documents"
    verbose_name = "اسناد"

    def ready(self):
        from apps.authorization.registry import (
            register_health_house_resolver,
            register_queryset_scope_resolver,
        )

        from .models import Document
        from .resolvers import document_health_houses, scope_document_queryset

        register_health_house_resolver(Document, document_health_houses)
        register_queryset_scope_resolver(Document, scope_document_queryset)