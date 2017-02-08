import os
import sys
import django
import datetime
import json

KEY_FILEPATH = "/home/ubuntu/prd-deploy/PrdDeployer/pem/"
LOG_FILE = "/home/ubuntu/ec2checker.log"
#timestamp = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d_%H-%M-%S")
#logfile = open(LOG_FILE%(timestamp,), 'a')
logfile = open(LOG_FILE, 'a')

# Initialize django environment:
sys.path.append(os.path.abspath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'PrdDeployer.settings'
django.setup()

import fabric
from fabric.api import *
from awscredentialmgr.models import AWSProfile, AWSRegion
from updateplanmgr.models import Module
from ec2mgr.models import EC2Instance
#from checktask import EC2CheckTask
from ec2checker import EC2Checker, CheckRunner
from django.conf import settings

PROFILE = "global-prd"
#REGION = "ap-southeast-1"
#REGION = "eu-west-1"
REGIONS = (
    "ap-southeast-1",
    "eu-west-1",
    "us-east-1"
)
#REGION = "us-east-1"


def check_region(profile_name, region_name, check_all=False):
    profile = AWSProfile.objects.get(name=profile_name)
    region = AWSRegion.objects.get(name=region_name)
    runners = []
    if check_all:
        filters = {
            'profile': profile,
            'region': region
        }
    else:
        filters = {
            'profile': profile,
            'region': region,
            'is_online_version': True
        }
    for module in Module.objects.filter(**filters):
        #print("========== %s =========="%(module.display_name))
        for ec2instance in module.instances.all():
            if ec2instance.running_state != "running":
                #print("    "+ec2instance.name+" not running. Skipped.")
                continue
            #print("    Instance: "+ec2instance.name)
            #print("    IP: "+ec2instance.private_ip_address)
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
    fabric.network.disconnect_all()


def main():
    check_all=False
    if len(sys.argv) > 1:
        if sys.argv[1] == "-a":
            check_all = True
    logfile.write("BEGIN: "+datetime.datetime.strftime(datetime.datetime.now(),"%Y-%m-%d %H:%M:%S"))
    logfile.write("\n")
    for region_name in REGIONS:
        check_region(PROFILE, region_name, check_all=check_all)
    logfile.write("END: "+datetime.datetime.strftime(datetime.datetime.now(),"%Y-%m-%d %H:%M:%S"))
    logfile.write("\n")
    logfile.close()


if __name__ == "__main__":
    main()

