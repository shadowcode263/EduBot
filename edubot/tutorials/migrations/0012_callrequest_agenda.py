# Generated by Django 3.2.12 on 2023-01-28 21:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tutorials', '0011_callrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='callrequest',
            name='agenda',
            field=models.TextField(default='Agenda'),
        ),
    ]