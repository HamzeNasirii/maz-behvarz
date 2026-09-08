from django.db import migrations

PERMISSION_CODES = [
    ("request.view", "مشاهده‌ی درخواست"),
    ("request.create", "ایجاد درخواست"),
    ("request.update", "ویرایش درخواست"),
    ("request.submit", "ارسال درخواست"),
    ("request.review", "بررسی درخواست"),
    ("request.approve", "تأیید درخواست"),
    ("request.reject", "رد درخواست"),
    ("request.return", "بازگشت درخواست"),
    ("request.cancel", "لغو درخواست"),
    ("request.complete", "تکمیل درخواست"),
    ("request.manage", "مدیریت کامل درخواست‌ها"),
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
        ("authorization", "0011_seed_document_permissions"),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]