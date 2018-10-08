# Generated by Django 2.1.2 on 2018-10-07 17:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('YtManagerApp', '0004_auto_20181005_1626'),
    ]

    operations = [
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel_id', models.TextField(unique=True)),
                ('username', models.TextField(null=True, unique=True)),
                ('custom_url', models.TextField(null=True, unique=True)),
                ('name', models.TextField()),
                ('description', models.TextField()),
                ('icon_default', models.TextField()),
                ('icon_best', models.TextField()),
                ('upload_playlist_id', models.TextField()),
            ],
        ),
        migrations.RenameField(
            model_name='subscription',
            old_name='url',
            new_name='playlist_id',
        ),
        migrations.AddField(
            model_name='subscription',
            name='description',
            field=models.TextField(default=None),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='subscription',
            name='icon_best',
            field=models.TextField(default=None),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='subscription',
            name='icon_default',
            field=models.TextField(default=None),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='subscription',
            name='channel',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='YtManagerApp.Channel'),
            preserve_default=False,
        ),
    ]
