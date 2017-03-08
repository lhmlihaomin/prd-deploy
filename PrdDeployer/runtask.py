import os
import sys
import django
import datetime
import json

KEY_FILEPATH = "/home/ubuntu/pem/"
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
from schtasks.ec2checker import EC2Checker, CheckRunner
from django.conf import settings

PROFILE = "cn-alpha"
REGIONS = (
    "cn-north-1",
)

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
            #'is_online_version': True
        }
    for module in Module.objects.filter(**filters):
        for ec2instance in module.instances.all():
            if check_all:
                if ec2instance.running_state not in ("running", "pending"):
                    continue
            else:
                if ec2instance.service_status != "not_ready":
                    continue
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
                                 settings.RUN_TIMEOUT)
            runners.append(CheckRunner(checker))
            #results = checker.perform_check()
            #checker.save_results(results)
    for runner in runners:
        runner.start()
    for runner in runners:
        runner.join()


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

