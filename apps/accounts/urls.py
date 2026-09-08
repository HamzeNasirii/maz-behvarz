from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("password-reset/bale/", views.bale_reset_request_view, name="bale_reset_request"),
    path("password-reset/bale/verify/", views.bale_reset_verify_view, name="bale_reset_verify"),
]