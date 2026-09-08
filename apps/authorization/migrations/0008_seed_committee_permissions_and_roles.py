from django.db import migrations

PERMISSION_CODES = [
    ("committee.create", "ایجاد کمیته"),
    ("committee.update", "ویرایش کمیته"),
    ("committee.delete", "حذف/بایگانی کمیته"),
    ("committee.manage_members", "مدیریت اعضای کمیته"),
    ("committee.approve", "تأیید تخصیصات کمیته"),
    ("committee.publish", "انتشار عمومی کمیته"),
]

ROLE_CODES = [
    ("COMMITTEE_SECRETARY", "دبیر کمیته", "مسئولیت دبیرخانه‌ی یک کمیته مشخص"),
]


def seed(apps, schema_editor):
    Permission = apps.get_model("authorization", "Permission")
    Role = apps.get_model("authorization", "Role")

    for code, description in PERMISSION_CODES:
        Permission.objects.get_or_create(code=code, defaults={"description": description})

    for code, name, description in ROLE_CODES:
        Role.objects.get_or_create(code=code, defaults={"name": name, "description": description})


def unseed(apps, schema_editor):
    Permission = apps.get_model("authorization", "Permission")
    Role = apps.get_model("authorization", "Role")
    Permission.objects.filter(code__in=[c for c, _ in PERMISSION_CODES]).delete()
    Role.objects.filter(code__in=[c for c, _, _ in ROLE_CODES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        # ⚠️ این رو با نام واقعی migration خودکار فاز ۳۰ اپ authorization جایگزین کن
        ("authorization", "0007_accessscope_committee"),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]