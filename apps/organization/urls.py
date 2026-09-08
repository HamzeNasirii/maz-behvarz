from django.urls import path

from . import views

app_name = "organization"

urlpatterns = [
    path("counties/", views.counties_by_province, name="counties_by_province"),
    path("networks/", views.networks_by_county, name="networks_by_county"),
    path("centers/", views.centers_by_network, name="centers_by_network"),
    path("houses/", views.houses_by_center, name="houses_by_center"),
]