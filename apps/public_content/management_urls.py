from django.urls import path

from . import management_views as views

app_name = "public_content_mgmt"

urlpatterns = [
    path("management/content/", views.hub_view, name="hub"),
    path("management/content/<str:content_type>/", views.list_view, name="list"),
    path("management/content/<str:content_type>/create/", views.create_view, name="create"),
    path("management/content/<str:content_type>/quick-category/", views.quick_category_create_view,
         name="quick_category_create"),
    path("management/content/tags/suggestions/", views.tag_suggestions_view, name="tag_suggestions"),
    path("management/content/news/<int:pk>/gallery/", views.news_gallery_view, name="news_gallery"),
    path("management/content/news/<int:pk>/gallery/<int:image_pk>/delete/", views.news_gallery_delete_view,
         name="news_gallery_delete"),
    path("management/content/tags/quick-create/", views.tag_quick_create_view, name="tag_quick_create"),
    path("management/content/documents/<int:pk>/attachments/", views.document_attachments_view,
         name="document_attachments"),
    path("management/content/documents/<int:pk>/attachments/<int:file_pk>/delete/",
         views.document_attachment_delete_view, name="document_attachment_delete"),
    path("management/content/<str:content_type>/<int:pk>/edit/", views.edit_view, name="edit"),
    path("management/content/<str:content_type>/<int:pk>/delete/", views.delete_view, name="delete"),
]