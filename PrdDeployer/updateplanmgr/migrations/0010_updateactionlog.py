# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-02-27 08:31
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('updateplanmgr', '0009_module_service_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='UpdateActionLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('source_ip', models.CharField(max_length=200)),
                ('action', models.CharField(max_length=500)),
                ('args', models.TextField(blank=True)),
                ('result', models.TextField(blank=True)),
                ('update_plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='updateplanmgr.UpdatePlan')),
                ('update_step', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='updateplanmgr.UpdateStep')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
