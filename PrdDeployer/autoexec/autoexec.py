import os
import sys

import django
import boto3

# Django setup:
# Django setup:
sys.path.append(
    os.path.abspath(
       os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir)
    )
)
os.environ['DJANGO_SETTINGS_MODULE'] = 'PrdDeployer.settings'
django.setup()

from updateplanmgr.models import UpdatePlan, UpdateStep, Module
from ec2mgr.ec2 import run_instances, add_instance_tags, add_volume_tags

# read update plan and step info:
try:
    plan_id = sys.argv[1]
    plan_id = int(plan_id)
except:
    print "Usage: python autoexec.py <updateplan_id>"
    exit()

plan = UpdatePlan.objects.get(pk=plan_id)
step = plan.get_current_step()
module = step.module
session = module.profile.get_session(module.region)
ec2 = session.resource('ec2')
elb = session.client('elb')

# deploy new versions:
instance_ids = run_instances(ec2, module, module.launch_count)
# register load balancers:
# deregister old versions:
