# Generated by Django 3.2.12 on 2023-01-27 23:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tutorials', '0008_alter_lesson_date_published'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lesson',
            name='file',
            field=models.FileField(blank=True, null=True, upload_to='lessons/'),
        ),
    ]
