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
#from checktask import EC2CheckTask
from ec2checker import EC2Checker
from django.conf import settings

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

def main():
    print(datetime.datetime.strftime(datetime.datetime.now(),"%H%M%S"))
    for module in Module.objects.filter(profile=profile, region=region, name__in=('dispatcher', 'assembler')):
        if not module.is_online_version:
            continue
        print("========== %s =========="%(module.display_name))
        for ec2instance in module.instances.all():
            print("    Instance: "+ec2instance.name)
            print("    IP: "+ec2instance.private_ip_address)
            #task = EC2CheckTask(module, ec2instance, KEY_FILEPATH)
            #task.set_fabric_env()
            #task.check_instance()
            checker = EC2Checker(module,
                                 ec2instance,
                                 KEY_FILEPATH,
                                 settings.SERVICE_TYPES,
                                 settings.TIME_ZONE,
                                 300)
            results = checker.perform_check()
            checker.save_results(results)
    print(datetime.datetime.strftime(datetime.datetime.now(),"%H%M%S"))


if __name__ == "__main__":
    main()

