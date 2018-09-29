import os
import sys

import django
import boto3

import time

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
from ec2mgr.models import EC2Instance
from ec2mgr.ec2 import run_instances, add_instance_tags_ex, add_volume_tags_ex


def retry(retry_times, callback, wait=0, *args, **kwargs):
    """
    Run a method repeatedly until it returns or exceeds retry times.

    Args:
        retry_times: (int) max times to retry;
        callback: (function) the action to retry;
        wait: (int) seconds to wait between each run;
        *args, **kwargs: args passed directly to callback;

    Return:
        the result returned by `callback`.
    """
    for i in range(retry_times):
        print("Making try {0} ...".format(i+1))
        try:
            result = callback(*args, **kwargs)
            return result
        except Exception as ex: 
            if i < retry_times - 1:
                time.sleep(wait)
            else:
                raise ex


def wait(timeout, interval, action, *args, **kwargs):
    """Retry `action` until it returns True or time out."""
    start_time = time.time()
    while True:
        result = action(*args, **kwargs)
        if result:
            print "Done."
            return True
        else:
            now = time.time()
            if now - start_time < timeout:
                print "Sleep {0} and try again ...".format(interval)
                time.sleep(interval)
            else:
                print "Timed out."
                return False


def deploy_new_version_aws(ec2, module):
    """Deploy new version on AWS EC2."""
    instance_ids = list()
    ec2instances = list()

    # start servers:
    ### run instances:
    instances = retry(3, run_instances, 10, ec2, module, module.launch_count)
    ### save instances to database:
    for instance in instances:
        ec2instance = EC2Instance(
            name="",
            instance_id=instance.id,
            private_ip_address=instance.private_ip_address,
            key_pair=instance.key_pair.name,
            running_state=instance.state['Name'],
            service_status="not_ready",
            note="Instance just started.",
            instance_created=True,
            instance_tags_added=False,
            volume_tags_added=False,
            vpc_id=instance.vpc_id
        )
        ec2instance.save()
        module.instances.add(ec2instance)
        instance_ids.append(instance.id)

    # add tags to EC2 instances:
    result = retry(3, add_instance_tags_ex, 10, ec2, module, instance_ids)
    for instance_id in result:
        if result[instance_id]:
            ec2instance = EC2Instance.objects.get(instance_id=instance_id)
            print ec2instance.id
            ec2instance.instance_tags_added = True
            ec2instance.name = result[instance_id]
            print ec2instance.name
            ec2instance.save()

    # add tags to EBS volumes:
    result = retry(3, add_volume_tags_ex, 10, ec2, instance_ids)
    for instance_id in result:
        if result[instance_id]:
            ec2instance = EC2Instance.objects.get(instance_id=instance_id)
            ec2instance.volume_tags_added = True
            ec2instance.save()

    # wait until service status is ok, or timeout:
    
    # return list of started instances:


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
deploy_new_version_aws(ec2, module)

# register load balancers:

# deregister old versions:
