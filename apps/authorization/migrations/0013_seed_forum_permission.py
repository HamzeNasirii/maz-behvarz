from django.db import migrations


def seed(apps, schema_editor):
    Permission = apps.get_model("authorization", "Permission")
    Permission.objects.get_or_create(
        code="forum.moderate", defaults={"description": "مدیریت پست/کامنت فروم"}
    )


def unseed(apps, schema_editor):
    apps.get_model("authorization", "Permission").objects.filter(code="forum.moderate").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("authorization", "0012_seed_request_permissions"),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]