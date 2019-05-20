import os
import sys
import django
import datetime
import json
import argparse

import boto3

# Initialize django environment:
sys.path.append(os.path.abspath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'PrdDeployer.settings'
django.setup()

from awscredentialmgr.models import AWSProfile, AWSRegion
from ec2mgr.models import EC2Instance
from updateplanmgr.models import Module

PROFILE_NAME = 'cn-prd'
REGION_NAME = 'cn-north-1'
profile = AWSProfile.objects.get(name=PROFILE_NAME)
region = AWSRegion.objects.get(name=REGION_NAME)
session = boto3.Session(profile_name=PROFILE_NAME, region_name=REGION_NAME)
ec2resource = session.resource('ec2')

print("Reading online instances ...")
instances_dict = {}
for instance in ec2resource.instances.all():
    instances_dict.update({
        instance.id: instance
    })

print("Reading local instances ...")
local_instances_dict = {}
for instance in EC2Instance.objects.exclude(running_state='terminated'):
    local_instances_dict.update({
        instance.instance_id: instance
    })

for local_instance_id in local_instances_dict.keys():
    local_instance = local_instances_dict[local_instance_id]

    if instances_dict.has_key(local_instance_id):
        instance = instances_dict[local_instance_id]
        if local_instance.running_state != instance.state['Name']:
            local_instance.running_state = instance.state['Name']
            local_instance.save()
        print(instance.state['Name'])
    else:
        print(local_instance_id+" is no more.")
        local_instance.running_state = 'terminated'
        local_instance.service_status = 'stopped'
        local_instance.retired = True
        local_instance.save()
