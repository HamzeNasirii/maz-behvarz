from django.db import migrations


def normalize_payment_methods(apps, schema_editor):
    """
    به‌جای مطابقت دقیق و شکننده با متن قدیمی (که حتی نیم‌فاصله‌اش هم
    می‌تواند چند کدگذاری یونیکد متفاوت داشته باشد)، بر پایه‌ی وجود یک
    کلمه‌ی کلیدی در متن آزاد قدیمی تشخیص می‌دهیم — مقاوم‌تر و کامل‌تر.
    """
    MembershipFee = apps.get_model("members", "MembershipFee")

    keyword_map = [
        ("بله", "bale"),
        ("نقد", "cash"),
        ("کارت", "card_to_card"),
    ]

    for fee in MembershipFee.objects.exclude(payment_method__in=["bale", "cash", "card_to_card", ""]):
        for keyword, new_code in keyword_map:
            if keyword in fee.payment_method:
                fee.payment_method = new_code
                fee.save(update_fields=["payment_method"])
                break


def reverse_normalize(apps, schema_editor):
    """این Migration معکوس‌پذیر نیست (متن اصلی قدیمی قابل بازسازی دقیق نیست) — بی‌عملیات."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("members", "0010_alter_feechangerequest_status"),
    ]
    operations = [
        migrations.RunPython(normalize_payment_methods, reverse_normalize),
    ]