from django.db import migrations

PERMISSION_CODES = [
    ("board.create", "ایجاد دوره‌ی هیئت‌مدیره"),
    ("board.update", "ویرایش دوره‌ی هیئت‌مدیره"),
    ("board.delete", "بایگانی دوره‌ی هیئت‌مدیره"),
    ("board.manage_members", "مدیریت اعضای هیئت‌مدیره"),
    ("board.approve", "تأیید تخصیصات هیئت‌مدیره"),
    ("board.publish", "انتشار عمومی هیئت‌مدیره"),
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
        # ⚠️ این را با اسم واقعی migration خودکار همین فاز جایگزین کن
        ("authorization", "0009_roleassignment_is_public_visible"),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]