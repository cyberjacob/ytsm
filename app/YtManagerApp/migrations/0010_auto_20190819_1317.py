# Generated by Django 2.2.4 on 2019-08-19 13:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('YtManagerApp', '0009_jobexecution_jobmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='rewrite_playlist_indices',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='video',
            name='new',
            field=models.BooleanField(default=True),
        ),
    ]