import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_existing_status(apps, schema_editor):
    Member = apps.get_model("members", "Member")
    Member.objects.filter(approval_status="approved").update(status="active")
    Member.objects.filter(approval_status="pending").update(status="under_review")
    Member.objects.filter(approval_status="rejected").update(status="rejected")


def reverse_migrate_existing_status(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('members', '0003_alter_member_options'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='member',
            name='status',
            field=models.CharField(
                choices=[('draft', 'پیش\u200cنویس'), ('submitted', 'ثبت\u200cشده'), ('under_review', 'در حال بررسی'),
                         ('approved', 'تأییدشده'), ('rejected', 'ردشده'), ('active', 'فعال'), ('suspended', 'معلق'),
                         ('expired', 'منقضی'), ('cancelled', 'لغوشده')], db_index=True, default='draft',
                help_text='چرخه\u200cی کامل عضویت (پس از پذیرش اولیه) — مستقل از approval_status', max_length=20),
        ),
        migrations.CreateModel(
            name='MembershipFee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=0, max_digits=12)),
                ('due_date', models.DateField()),
                ('payment_status', models.CharField(
                    choices=[('unpaid', 'پرداخت\u200cنشده'), ('paid', 'پرداخت\u200cشده'), ('waived', 'معاف')],
                    db_index=True, default='unpaid', max_length=10)),
                ('payment_date', models.DateField(blank=True, null=True)),
                ('payment_method', models.CharField(blank=True, max_length=50)),
                ('reference_number', models.CharField(blank=True, max_length=100)),
                ('receipt', models.FileField(blank=True, null=True, upload_to='members/fee_receipts/%Y/%m/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='fees',
                                             to='members.member')),
            ],
            options={
                'verbose_name': 'حق عضویت',
                'verbose_name_plural': 'حق\u200cهای عضویت',
                'ordering': ['-due_date'],
            },
        ),
        migrations.CreateModel(
            name='MembershipStatusHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('previous_status', models.CharField(choices=[('draft', 'پیش\u200cنویس'), ('submitted', 'ثبت\u200cشده'),
                                                              ('under_review', 'در حال بررسی'),
                                                              ('approved', 'تأییدشده'), ('rejected', 'ردشده'),
                                                              ('active', 'فعال'), ('suspended', 'معلق'),
                                                              ('expired', 'منقضی'), ('cancelled', 'لغوشده')],
                                                     max_length=20)),
                ('new_status', models.CharField(choices=[('draft', 'پیش\u200cنویس'), ('submitted', 'ثبت\u200cشده'),
                                                         ('under_review', 'در حال بررسی'), ('approved', 'تأییدشده'),
                                                         ('rejected', 'ردشده'), ('active', 'فعال'),
                                                         ('suspended', 'معلق'), ('expired', 'منقضی'),
                                                         ('cancelled', 'لغوشده')], max_length=20)),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('comment', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                            related_name='membership_status_changes', to=settings.AUTH_USER_MODEL)),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='status_history',
                                             to='members.member')),
            ],
            options={
                'verbose_name': 'تاریخچه\u200cی وضعیت عضویت',
                'verbose_name_plural': 'تاریخچه\u200cهای وضعیت عضویت',
                'ordering': ['-created_at'],
            },
        ),
        migrations.RunPython(migrate_existing_status, reverse_migrate_existing_status),
    ]