# Generated by Django 3.2.12 on 2023-01-27 23:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tutorials', '0006_auto_20230128_0130'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lesson',
            name='date_published',
            field=models.DateTimeField(auto_now_add=True, verbose_name='date published'),
        ),
    ]
