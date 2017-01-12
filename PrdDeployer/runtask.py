import os
import sys
import django
import datetime
import json

KEY_FILEPATH = "/home/ubuntu/PrdDeployer/pem/"

# Initialize django environment:
sys.path.append(os.path.abspath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'PrdDeployer.settings'
django.setup()


from fabric.api import *
from updateplanmgr.models import Module
from ec2mgr.models import EC2Instance
from checktask import EC2CheckTask

module = Module.objects.get(name='mod1', current_version='1.2.1')
for ec2instance in module.instances.all():
    task = EC2CheckTask(ec2instance, KEY_FILEPATH)
    task.set_fabric_env()

