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
from ec2checker import EC2Checker, CheckRunner
from django.conf import settings

PROFILE = "global-prd"
REGION = "ap-southeast-1"
#REGION = "us-east-1"
profile = AWSProfile.objects.get(name=PROFILE)
region = AWSRegion.objects.get(name=REGION)


def main():
    # Record start time:
    print(datetime.datetime.strftime(datetime.datetime.now(),"%H%M%S"))
    runners = []
    for module in Module.objects.filter(profile=profile, region=region, is_online_version=True):
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
            runners.append(CheckRunner(checker))
            #results = checker.perform_check()
            #checker.save_results(results)
    for runner in runners:
        runner.start()
    for runner in runners:
        runner.join()
    # Record finish time:
    print(datetime.datetime.strftime(datetime.datetime.now(),"%H%M%S"))


if __name__ == "__main__":
    main()

