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
from schtasks.ec2stopper import EC2Stopper, StopperRunner
from django.conf import settings
#from django.db.models import Q

KEY_FILEPATH = settings.PEM_DIR

"""
module = Module.objects.get(pk=7)
instance = EC2Instance.objects.get(pk=8)
"""

def main():
    """Multi-thread (parallel) stopping."""
    for module in Module.objects.all():
        ec2instances = module.instances.filter(service_status__in=('to_stop', 'stopped'))
        #ec2instances = module.instances.all()
        runners = []
        for ec2instance in ec2instances:
            print(ec2instance.name)
            stopper = EC2Stopper(module,
                                 ec2instance,
                                 settings.PEM_DIR,
                                 settings.SERVICE_TYPES,
                                 settings.TIME_ZONE,
                                 settings.STOP_TIMEOUT)
            runners.append(StopperRunner(stopper))
        for runner in runners:
            runner.start()
        for runner in runners:
            runner.join()


def main1():
    """Serial stopping."""
    for module in Module.objects.all():
        ec2instances = module.instances.filter(service_status__in=('to_stop', 'stopped'))
        stoppers = []
        for ec2instance in ec2instances:
            stopper = EC2Stopper(module,
                                 ec2instance,
                                 settings.PEM_DIR,
                                 settings.SERVICE_TYPES,
                                 settings.TIME_ZONE,
                                 settings.STOP_TIMEOUT)
            stoppers.append(stopper)

        for stopper in stoppers:
            #actions, cmds = stopper.assemble_stop_cmd()
            #print(cmds)
            results = stopper.run_stop_commands()
            print(results)

if __name__ == "__main__":
    main1()
