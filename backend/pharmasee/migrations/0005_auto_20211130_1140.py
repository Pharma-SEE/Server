# Generated by Django 3.0.14 on 2021-11-30 02:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmasee', '0004_auto_20211130_0626'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reminder',
            name='taken_time',
            field=models.TimeField(blank=True),
        ),
    ]