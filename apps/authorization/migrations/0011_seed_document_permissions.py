from django.db import migrations

PERMISSION_CODES = [
    ("document.upload", "آپلود سند"),
    ("document.view", "مشاهده‌ی سند"),
    ("document.update", "ویرایش سند"),
    ("document.approve", "تأیید سند"),
    ("document.publish", "انتشار سند"),
    ("document.delete", "بایگانی سند"),
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
        # ⚠️ این را با اسم واقعی آخرین migration این اپ جایگزین کن
        ("authorization", "0010_seed_board_permissions"),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]