# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-02-28 09:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('updateplanmgr', '0011_auto_20170228_1430'),
    ]

    operations = [
        migrations.AlterField(
            model_name='updateplan',
            name='steps',
            field=models.ManyToManyField(related_name='update_plan', to='updateplanmgr.UpdateStep'),
        ),
    ]
