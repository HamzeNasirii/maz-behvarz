from django.db import migrations

PERMISSION_CODES = [
    ("membership.review", "بررسی درخواست عضویت"),
    ("membership.approve", "تأیید/فعال‌سازی عضویت"),
    ("membership.suspend", "تعلیق عضویت"),
    ("membership.reinstate", "اعاده‌ی عضویت"),
    ("membership.expire", "اعلام انقضای عضویت"),
    ("membership.cancel", "لغو عضویت"),
    ("membership.fee.view", "مشاهده‌ی حق عضویت"),
    ("membership.fee.update", "ثبت پرداخت حق عضویت"),
]


def seed(apps, schema_editor):
    Permission = apps.get_model("authorization", "Permission")
    for code, description in PERMISSION_CODES:
        Permission.objects.get_or_create(code=code, defaults={"description": description})


def unseed(apps, schema_editor):
    Permission = apps.get_model("authorization", "Permission")
    Permission.objects.filter(code__in=[c for c, _ in PERMISSION_CODES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("authorization", "0004_roleassignment_approval_status_and_more"),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]