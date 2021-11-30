# Generated by Django 3.0.14 on 2021-11-29 21:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('pharmasee', '0003_auto_20211129_1958'),
    ]

    operations = [
        migrations.AddField(
            model_name='reminder',
            name='dose_taken_today',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='reminder',
            name='is_taken_today',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='reminder',
            name='user_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reminders', to=settings.AUTH_USER_MODEL),
        ),
    ]