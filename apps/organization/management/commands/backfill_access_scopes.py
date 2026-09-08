from django.core.management.base import BaseCommand

from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province
from apps.organization.scope_sync import ensure_access_scope_for


class Command(BaseCommand):
    help = "برای همه‌ی رکوردهای سازمانی موجود، AccessScope متناظر (اگر وجود نداشت) می‌سازد."

    def handle(self, *args, **options):
        counts = {"province": 0, "county": 0, "network": 0, "center": 0, "house": 0}

        for province in Province.objects.all():
            ensure_access_scope_for("province", province)
            counts["province"] += 1

        for county in County.objects.all():
            ensure_access_scope_for("county", county)
            counts["county"] += 1

        for network in HealthNetwork.objects.all():
            ensure_access_scope_for("network", network)
            counts["network"] += 1

        for center in HealthCenter.objects.all():
            ensure_access_scope_for("center", center)
            counts["center"] += 1

        for house in HealthHouse.objects.all():
            ensure_access_scope_for("house", house)
            counts["house"] += 1

        self.stdout.write(self.style.SUCCESS(f"محدوده‌های دسترسی همگام‌سازی شدند: {counts}"))