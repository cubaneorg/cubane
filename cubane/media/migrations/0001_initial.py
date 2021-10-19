# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2019-02-15 14:39
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Media',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(db_index=True, editable=False, null=True, verbose_name='Created on')),
                ('updated_on', models.DateTimeField(db_index=True, editable=False, null=True, verbose_name='Updated on')),
                ('deleted_on', models.DateTimeField(blank=True, db_index=True, editable=False, null=True, verbose_name='Deleted on')),
                ('uid', models.CharField(db_index=True, editable=False, max_length=64, null=True, unique=True, verbose_name='Unique ID')),
                ('hashid', models.CharField(db_index=True, editable=False, max_length=64, null=True, unique=True, verbose_name='Unique ID (Hashed)')),
                ('share_enabled', models.BooleanField(db_index=True, default=False, help_text='Enable file sharing for this media asset.', verbose_name='Share Enabled')),
                ('share_filename', models.CharField(blank=True, db_index=True, help_text='Public filename under which the system will make this document or image publicly available for download.', max_length=255, null=True, verbose_name='Public Filename')),
                ('caption', models.CharField(db_index=True, max_length=255)),
                ('credits', models.CharField(blank=True, max_length=255, null=True)),
                ('filename', models.CharField(max_length=255)),
                ('width', models.IntegerField(default=0)),
                ('height', models.IntegerField(default=0)),
                ('is_image', models.BooleanField(db_index=True, default=True)),
                ('has_preview', models.BooleanField(db_index=True, default=False)),
                ('is_member_image', models.BooleanField(default=False)),
                ('is_blank', models.BooleanField(db_index=True, default=False)),
                ('member_id', models.IntegerField(blank=True, null=True)),
                ('extra_image_title', models.CharField(blank=True, max_length=4000, null=True)),
                ('is_svg', models.BooleanField(default=False)),
                ('auto_fit', models.BooleanField(default=False)),
                ('external_url', models.CharField(db_index=True, max_length=255, null=True, unique=True)),
                ('version', models.IntegerField(blank=True, editable=False, null=True)),
                ('org_quality', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('jpeg_quality', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('focal_x', models.FloatField(blank=True, null=True)),
                ('focal_y', models.FloatField(blank=True, null=True)),
                ('created_by', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('deleted_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Deleted by')),
            ],
            options={
                'ordering': ['caption'],
                'db_table': 'cubane_media',
                'verbose_name': 'Media',
                'verbose_name_plural': 'Media',
            },
        ),
        migrations.CreateModel(
            name='MediaFolder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(db_index=True, editable=False, null=True, verbose_name='Created on')),
                ('updated_on', models.DateTimeField(db_index=True, editable=False, null=True, verbose_name='Updated on')),
                ('deleted_on', models.DateTimeField(blank=True, db_index=True, editable=False, null=True, verbose_name='Deleted on')),
                ('title', models.CharField(db_index=True, help_text='The name of the folder.', max_length=255, verbose_name='Folder Name')),
                ('created_by', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Created by')),
                ('deleted_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Deleted by')),
                ('parent', models.ForeignKey(blank=True, help_text='The parent folder of this folder or empty.', null=True, on_delete=django.db.models.deletion.CASCADE, to='media.MediaFolder', verbose_name='Parent Folder')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Updated by')),
            ],
            options={
                'ordering': ['title'],
                'db_table': 'cubane_mediafolder',
                'verbose_name': 'Media Folder',
                'verbose_name_plural': 'Media Folders',
            },
        ),
        migrations.CreateModel(
            name='MediaGallery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('seq', models.IntegerField(db_index=True, default=0, editable=False, help_text='The sequence number determines the order in which media assets are presented, for example within a list of gallery items or a carousel.', verbose_name='Sequence')),
                ('target_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('media', models.ForeignKey(help_text='The media assets that is part of a gallery.', on_delete=django.db.models.deletion.CASCADE, to='media.Media', verbose_name='Media')),
            ],
            options={
                'ordering': ['seq'],
                'db_table': 'cubane_media_gallery',
                'verbose_name': 'Media Gallery',
                'verbose_name_plural': 'Media Galleries',
            },
        ),
        migrations.AddField(
            model_name='media',
            name='parent',
            field=models.ForeignKey(blank=True, help_text='The folder this media asset is stored.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='media.MediaFolder', verbose_name='Folder'),
        ),
        migrations.AddField(
            model_name='media',
            name='updated_by',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Updated by'),
        ),
    ]