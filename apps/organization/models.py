from django.db import models

from .managers import (
    BaseOrganizationQuerySet,
    CountyQuerySet,
    HealthNetworkQuerySet,
    HealthCenterQuerySet,
    HealthHouseQuerySet,
)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Province(TimeStampedModel):
    name = models.CharField(max_length=100, db_index=True)
    code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    objects = BaseOrganizationQuerySet.as_manager()

    class Meta:
        verbose_name = "استان"
        verbose_name_plural = "استان‌ها"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name"], name="uniq_province_name"),
        ]

    def __str__(self):
        return self.name


class County(TimeStampedModel):
    province = models.ForeignKey(
        Province, on_delete=models.PROTECT, related_name="counties", db_index=True
    )
    name = models.CharField(max_length=100, db_index=True)
    code = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    objects = CountyQuerySet.as_manager()

    class Meta:
        verbose_name = "شهرستان"
        verbose_name_plural = "شهرستان‌ها"
        ordering = ["province__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["province", "name"], name="uniq_county_name_per_province"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.province.name})"


class HealthNetwork(TimeStampedModel):
    county = models.ForeignKey(
        County, on_delete=models.PROTECT, related_name="health_networks", db_index=True
    )
    name = models.CharField(max_length=150, db_index=True)
    code = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    objects = HealthNetworkQuerySet.as_manager()

    class Meta:
        verbose_name = "شبکه بهداشت و درمان"
        verbose_name_plural = "شبکه‌های بهداشت و درمان"
        ordering = ["county__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["county", "name"], name="uniq_network_name_per_county"
            ),
        ]

    @property
    def province(self):
        return self.county.province

    def __str__(self):
        return f"{self.name} ({self.county.name})"


class HealthCenter(TimeStampedModel):
    network = models.ForeignKey(
        HealthNetwork, on_delete=models.PROTECT, related_name="health_centers", db_index=True
    )
    name = models.CharField(max_length=150, db_index=True)
    code = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    objects = HealthCenterQuerySet.as_manager()

    class Meta:
        verbose_name = "مرکز خدمات جامع سلامت"
        verbose_name_plural = "مراکز خدمات جامع سلامت"
        ordering = ["network__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["network", "name"], name="uniq_center_name_per_network"
            ),
        ]

    @property
    def county(self):
        return self.network.county

    @property
    def province(self):
        return self.network.county.province

    def __str__(self):
        return f"{self.name} ({self.network.name})"


class HealthHouse(TimeStampedModel):
    center = models.ForeignKey(
        HealthCenter, on_delete=models.PROTECT, related_name="health_houses", db_index=True
    )
    name = models.CharField(max_length=150, db_index=True)
    code = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

    objects = HealthHouseQuerySet.as_manager()

    class Meta:
        verbose_name = "خانه بهداشت"
        verbose_name_plural = "خانه‌های بهداشت"
        ordering = ["center__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["center", "name"], name="uniq_house_name_per_center"
            ),
        ]

    @property
    def network(self):
        return self.center.network

    @property
    def county(self):
        return self.center.network.county

    @property
    def province(self):
        return self.center.network.county.province

    def __str__(self):
        return f"{self.name} ({self.center.name})"