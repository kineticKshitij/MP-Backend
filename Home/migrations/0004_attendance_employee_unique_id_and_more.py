# Generated by Django 4.1.13 on 2025-04-21 12:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Home', '0003_remove_employeesignup_is_superuser_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendance',
            name='employee_unique_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='attendance',
            name='organization_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
