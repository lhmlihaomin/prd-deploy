import os
import sys
import django
import datetime
import json

KEY_FILEPATH = "/home/ubuntu/prd-deploy/PrdDeployer/pem/"

# Initialize django environment:
sys.path.append(os.path.abspath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'PrdDeployer.settings'
django.setup()


from fabric.api import *
from awscredentialmgr.models import AWSProfile, AWSRegion
from updateplanmgr.models import Module
from ec2mgr.models import EC2Instance
from checktask import EC2CheckTask

PROFILE = "global-prd"
#REGION = "ap-southeast-1"
REGION = "us-east-1"
profile = AWSProfile.objects.get(name=PROFILE)
region = AWSRegion.objects.get(name=REGION)

"""
module = Module.objects.get(name='mod1', current_version='1.2.1')
for ec2instance in module.instances.all():
    task = EC2CheckTask(ec2instance, KEY_FILEPATH)
    task.set_fabric_env()
"""
for module in Module.objects.filter(profile=profile, region=region):
    print("========== %s =========="%(module.display_name))
    for ec2instance in module.instances.all():
        print("    Instance: "+ec2instance.name)
        print("    IP: "+ec2instance.private_ip_address)
        task = EC2CheckTask(module, ec2instance, KEY_FILEPATH)
        task.set_fabric_env()
        task.check_instance()

