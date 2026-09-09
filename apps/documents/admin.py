from django.contrib import admin

from .models import Document, DocumentStatusHistory


class DocumentStatusHistoryInline(admin.TabularInline):
    model = DocumentStatusHistory
    extra = 0
    readonly_fields = ("previous_status", "new_status", "actor", "reason", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "document_type", "visibility", "status", "is_archived", "created_at")
    list_filter = ("document_type", "visibility", "status", "is_archived")
    search_fields = ("title", "checksum")
    autocomplete_fields = ("uploaded_by", "scope")
    readonly_fields = ("status", "checksum", "file_size", "mime_type")
    inlines = [DocumentStatusHistoryInline]