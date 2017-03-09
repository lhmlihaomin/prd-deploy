import os
import sys
import django
import datetime
import json


sys.path.append(os.path.abspath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'PrdDeployer.settings'
django.setup()

from awscredentialmgr.models import AWSProfile, AWSRegion
from updateplanmgr.models import Module
from ec2mgr.models import EC2Instance
#from checktask import EC2CheckTask
from schtasks.ec2stopper import EC2Stopper
from django.conf import settings
#from django.db.models import Q

KEY_FILEPATH = settings.PEM_DIR

"""
module = Module.objects.get(pk=7)
instance = EC2Instance.objects.get(pk=8)
"""

def main():
    for module in Module.objects.all():
        ec2instances = module.instances.filter(service_status__in=('to_stop', 'stopped'))
        for ec2instance in ec2instances:
            print(ec2instance.name)
            