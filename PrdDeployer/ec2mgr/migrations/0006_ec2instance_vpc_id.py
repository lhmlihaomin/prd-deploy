# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-01-20 06:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ec2mgr', '0005_auto_20170113_1433'),
    ]

    operations = [
        migrations.AddField(
            model_name='ec2instance',
            name='vpc_id',
            field=models.CharField(default=b'', max_length=500),
        ),
    ]