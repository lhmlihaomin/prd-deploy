# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-03-08 02:41
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('awscredentialmgr', '0005_awsprofile_service_dir_prefix'),
    ]

    operations = [
        migrations.AddField(
            model_name='awsprofile',
            name='instance_prefix',
            field=models.CharField(blank=True, default=b'prd', max_length=500),
        ),
    ]
