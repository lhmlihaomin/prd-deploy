# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-07-21 02:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('updateplanmgr', '0012_auto_20170228_1701'),
    ]

    operations = [
        migrations.AlterField(
            model_name='module',
            name='instances',
            field=models.ManyToManyField(related_name='modules', to='ec2mgr.EC2Instance'),
        ),
    ]
