from django.contrib import admin

from .models import Province, County, HealthNetwork, HealthCenter, HealthHouse


@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    search_fields = ("name", "code")
    list_filter = ("is_active",)
    ordering = ("name",)


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = ("name", "province", "code", "is_active", "created_at")
    search_fields = ("name", "code", "province__name")
    list_filter = ("is_active", "province")
    ordering = ("province__name", "name")
    autocomplete_fields = ("province",)


@admin.register(HealthNetwork)
class HealthNetworkAdmin(admin.ModelAdmin):
    list_display = ("name", "county", "code", "is_active", "created_at")
    search_fields = ("name", "code", "county__name")
    list_filter = ("is_active", "county__province", "county")
    ordering = ("county__name", "name")
    autocomplete_fields = ("county",)


@admin.register(HealthCenter)
class HealthCenterAdmin(admin.ModelAdmin):
    list_display = ("name", "network", "code", "is_active", "created_at")
    search_fields = ("name", "code", "network__name")
    list_filter = ("is_active", "network__county", "network")
    ordering = ("network__name", "name")
    autocomplete_fields = ("network",)


@admin.register(HealthHouse)
class HealthHouseAdmin(admin.ModelAdmin):
    list_display = ("name", "center", "code", "is_active", "created_at")
    search_fields = ("name", "code", "center__name")
    list_filter = ("is_active", "center__network", "center")
    ordering = ("center__name", "name")
    autocomplete_fields = ("center",)