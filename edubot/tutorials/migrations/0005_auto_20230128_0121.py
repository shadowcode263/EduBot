# Generated by Django 3.2.12 on 2023-01-27 23:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tutorials', '0004_alter_tutorial_date_published'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lesson',
            name='instructions',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='lesson',
            name='tutorial_class',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tutorial_class', to='tutorials.tutorial'),
        ),
    ]
