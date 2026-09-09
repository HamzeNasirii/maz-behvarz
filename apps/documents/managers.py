from django.contrib.contenttypes.models import ContentType


def get_documents_for(obj):
    from .models import Document

    content_type = ContentType.objects.get_for_model(type(obj))
    return Document.objects.filter(
        content_type=content_type, object_id=obj.pk, is_archived=False
    )