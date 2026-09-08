from django.urls import path

from . import views

app_name = "employment"

urlpatterns = [
    path("management/employment/", views.employment_list_view, name="list"),
    path("management/employment/create/", views.employment_create_view, name="create"),
    path("management/employment/<int:pk>/", views.employment_detail_view, name="detail"),
    path("management/employment/<int:pk>/end/", views.employment_end_view, name="end"),
]