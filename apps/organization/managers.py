from django.db import models


class BaseOrganizationQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)


class CountyQuerySet(BaseOrganizationQuerySet):
    def by_province(self, province):
        return self.filter(province=province)


class HealthNetworkQuerySet(BaseOrganizationQuerySet):
    def by_county(self, county):
        return self.filter(county=county)


class HealthCenterQuerySet(BaseOrganizationQuerySet):
    def by_network(self, network):
        return self.filter(network=network)


class HealthHouseQuerySet(BaseOrganizationQuerySet):
    def by_center(self, center):
        return self.filter(center=center)