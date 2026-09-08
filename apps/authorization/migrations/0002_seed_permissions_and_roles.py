from django.db import migrations

PERMISSION_CODES = [
    ("member.view", "مشاهده‌ی عضو"),
    ("member.create", "ایجاد عضو"),
    ("member.update", "ویرایش عضو"),
    ("member.delete", "حذف عضو"),
    ("member.approve", "تأیید عضو"),
    ("member.export", "خروجی‌گیری از اعضا"),
    ("employment.view", "مشاهده‌ی محل خدمت"),
    ("employment.create", "ایجاد محل خدمت"),
    ("employment.update", "ویرایش محل خدمت"),
    ("employment.transfer", "جابه‌جایی محل خدمت"),
    ("employment.approve", "تأیید محل خدمت"),
    ("employment.history.view", "مشاهده‌ی تاریخچه‌ی محل خدمت"),
    ("role.view", "مشاهده‌ی نقش"),
    ("role.assign", "تخصیص نقش"),
    ("role.revoke", "لغو نقش"),
    ("role.approve", "تأیید نقش"),
    ("committee.view", "مشاهده‌ی کمیته"),
    ("committee.manage", "مدیریت کمیته"),
    ("board.view", "مشاهده‌ی هیئت‌مدیره"),
    ("board.manage", "مدیریت هیئت‌مدیره"),
    ("audit.view", "مشاهده‌ی گزارش‌ها"),
    ("audit.export", "خروجی‌گیری از گزارش‌ها"),
]

ROLE_CODES = [
    ("BEHVARZ", "بهورز", "نقش پایه‌ی عضویت بهورزی"),
    ("COUNTY_REPRESENTATIVE", "نماینده شهرستان", "نماینده‌ی انجمن در سطح یک شهرستان"),
    ("COMMITTEE_MANAGER", "مسئول کمیته", "مسئولیت اداره‌ی یک کمیته"),
    ("BOARD_MEMBER", "عضو هیئت‌مدیره", "عضویت در هیئت‌مدیره‌ی انجمن"),
]


def seed_permissions_and_roles(apps, schema_editor):
    Permission = apps.get_model("authorization", "Permission")
    Role = apps.get_model("authorization", "Role")

    for code, description in PERMISSION_CODES:
        Permission.objects.get_or_create(code=code, defaults={"description": description})

    for code, name, description in ROLE_CODES:
        Role.objects.get_or_create(
            code=code, defaults={"name": name, "description": description}
        )


def remove_permissions_and_roles(apps, schema_editor):
    Permission = apps.get_model("authorization", "Permission")
    Role = apps.get_model("authorization", "Role")
    Permission.objects.filter(code__in=[c for c, _ in PERMISSION_CODES]).delete()
    Role.objects.filter(code__in=[c for c, _, _ in ROLE_CODES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("authorization", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_permissions_and_roles, remove_permissions_and_roles),
    ]