from django.http import JsonResponse

from .models import County, HealthCenter, HealthHouse, HealthNetwork


def counties_by_province(request):
    province_id = request.GET.get("province")
    counties = County.objects.filter(province_id=province_id, is_active=True).order_by("name")
    return JsonResponse({"results": [{"id": c.id, "name": c.name} for c in counties]})


def networks_by_county(request):
    county_id = request.GET.get("county")
    networks = HealthNetwork.objects.filter(county_id=county_id, is_active=True).order_by("name")
    return JsonResponse({"results": [{"id": n.id, "name": n.name} for n in networks]})


def centers_by_network(request):
    network_id = request.GET.get("network")
    centers = HealthCenter.objects.filter(network_id=network_id, is_active=True).order_by("name")
    return JsonResponse({"results": [{"id": c.id, "name": c.name} for c in centers]})


def houses_by_center(request):
    center_id = request.GET.get("center")
    houses = HealthHouse.objects.filter(center_id=center_id, is_active=True).order_by("name")
    return JsonResponse({"results": [{"id": h.id, "name": h.name} for h in houses]})