# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-04-28 03:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ec2mgr', '0007_ec2instance_service_stopped_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='ec2instance',
            name='retired',
            field=models.BooleanField(default=False),
        ),
    ]