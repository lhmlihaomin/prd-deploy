# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-01-04 02:19
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('updateplanmgr', '0004_remove_updatestep_previous_module'),
    ]

    operations = [
        migrations.AddField(
            model_name='updateplan',
            name='finished',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='updateplan',
            name='start_time',
            field=models.DateTimeField(default=datetime.datetime(2017, 1, 4, 2, 19, 8, 885000, tzinfo=utc)),
        ),
    ]
