# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-01-09 07:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ec2mgr', '0002_auto_20170106_1133'),
    ]

    operations = [
        migrations.AddField(
            model_name='ec2instance',
            name='instance_created',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='ec2instance',
            name='instance_tags_added',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='ec2instance',
            name='volume_tags_added',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='ec2instance',
            name='instance_id',
            field=models.CharField(default=b'', max_length=500),
        ),
        migrations.AlterField(
            model_name='ec2instance',
            name='key_pair',
            field=models.CharField(default=b'', max_length=100),
        ),
        migrations.AlterField(
            model_name='ec2instance',
            name='note',
            field=models.TextField(default=b''),
        ),
        migrations.AlterField(
            model_name='ec2instance',
            name='private_ip_address',
            field=models.CharField(default=b'', max_length=100),
        ),
        migrations.AlterField(
            model_name='ec2instance',
            name='running_state',
            field=models.CharField(default=b'', max_length=100),
        ),
        migrations.AlterField(
            model_name='ec2instance',
            name='service_status',
            field=models.CharField(default=b'', max_length=100),
        ),
    ]