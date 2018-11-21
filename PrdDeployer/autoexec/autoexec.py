#!/usr/bin/python
# coding: utf8
# Execute the first available step of the specified UpdatePlan.
# Usage:
#     python autoexec.py <updateplan_id>
# TODO:
#   1. create a lock when running;
#   2. mark updateplan as finished when all steps are finished;
#   3. rollback ability;


import os
import sys
import traceback

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

from django.contrib.auth.models import User
from django.conf import settings

from updateplanmgr.models import UpdatePlan, UpdateStep, Module, UpdateActionLog
from ec2mgr.models import EC2Instance
from ec2mgr.ec2 import run_instances, add_instance_tags_ex, add_volume_tags_ex
from openfalcon import openfalcon_login, openfalcon_logout, openfalcon_disable

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
        print "Running action ..."
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


def disable_module_alarm(module):
    instances = module.instances.all()
    session = openfalcon_login(
        settings.OPENFALCON['login_url'],
        settings.OPENFALCON['username'],
        settings.OPENFALCON['password'],
        settings.OPENFALCON['cert_file'],
        settings.OPENFALCON['cert_key'],
        False
    )

    result = openfalcon_disable(
        session,
        settings.OPENFALCON['switch_url'],
        instances
    )
    if not result:
        raise Exception("Disable alarm failed.")

    openfalcon_logout(
        session,
        settings.OPENFALCON['logout_url']
    )
    return True


def all_instances_service_ok(instance_ids):
    for ec2instance in EC2Instance.objects.filter(instance_id__in=instance_ids):
        print ec2instance.service_status
        if ec2instance.service_status != 'ok':
            return False
    return True


def start_module_aws(ec2, module):
    """Deploy new version on AWS EC2."""
    print "Deploying new version instances ..."

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
        ec2instances.append(ec2instance)
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
    result = wait(360, 30, all_instances_service_ok, instance_ids)
    if not result:
        # TODO: handle exception
        raise Exception("Service failed to start")
        pass
    
    # return list of started instances:
    print "Instances: {0}".format(instance_ids)
    return ec2instances


def all_instances_in_service(elb, load_balancer_names, instances):
    for load_balancer_name in load_balancer_names:
        result = elb.describe_instance_health(
            LoadBalancerName=load_balancer_name,
            Instances=instances
        )
        for state in result['InstanceStates']:
            if state['State'] != 'InService':
                return False
    return True


def lbreg_module_aws(elb, module):
    print "Registering instances with load balancers ..."

    # parse load balancer names:
    lb_names = list()
    for i in module.load_balancer_names.split(','):
        lb_name = i.strip()
        if len(lb_name) > 0:
            lb_names.append(lb_name)
    # get ec2instance list:
    Instances = map(
        lambda x: {'InstanceId': x},
        #[instance.instance_id for instance in module.instances.all()]
        # edit: only register instances with services running:
        [instance.instance_id for instance in module.instances.filter(service_status='ok')]
    )
    # register with each load balancer:
    for LoadBalancerName in lb_names:
        result = elb.register_instances_with_load_balancer(
            LoadBalancerName=LoadBalancerName,
            Instances=Instances
        )
        for i in Instances:
            if i not in result['Instances']:
                msg = "Register failed: {0} - {1}".format(LoadBalancerName, i['InstanceId'])
                raise Exception(msg)
    
    # wait for new instances become "InService":
    result = wait(300, 30, all_instances_in_service, elb, lb_names, Instances)
    if not result:
        # TODO: Log exception
        return False
        
    print "Done."
    return True


def lbdereg_module_aws(elb, module):
    print "Deregistering instances from load balancers ..."

    # parse load balancer names:
    lb_names = list()
    for i in module.load_balancer_names.split(','):
        lb_name = i.strip()
        if len(lb_name) > 0:
            lb_names.append(lb_name)
    # get ec2instance list:
    Instances = map(
        lambda x: {'InstanceId': x},
        #[instance.instance_id for instance in module.instances.all()]
        # edit: only register instances with services running:
        [instance.instance_id for instance in module.instances.filter(service_status='ok')]
    )
    # register with each load balancer:
    for LoadBalancerName in lb_names:
        result = elb.deregister_instances_from_load_balancer(
            LoadBalancerName=LoadBalancerName,
            Instances=Instances
        )
        for i in Instances:
            if i in result['Instances']:
                msg = "Deregister failed: {0} - {1}".format(LoadBalancerName, i['InstanceId'])
                raise Exception(msg)

    print "Done."
    return True


def stop_module_aws(module):
    print "Stopping old instances ..."

    instances = module.instances.all()
    ids = [str(instance.id) for instance in instances]
    # script path:
    stop_script = os.path.sep.join([
        os.path.abspath(
            os.path.sep.join([
                os.path.dirname(
                    os.path.abspath(__file__)
                ),
                '..'
            ])
        ),
        'stop_ec2_instances.py'
    ])
    cmd = [
        'python',
        stop_script,
    ]
    cmd += ids
    #subprocess.Popen(cmd)
    print cmd

    print "Done."
    return True


def poweron_module_aws(ec2client, module):
    """Turn on stopped EC2 instances"""
    InstanceIds = []    # EC2 Instance "ID"s;
    instance_ids = []   # database table ids;
    for instance in module.instances.all():
        InstanceIds.append(instance.instance_id)
        instance_ids.append(instance.id)
    result = ec2client.start_instances(InstanceIds=InstanceIds)
    for r in result['StartingInstances']:
        if r['CurrentState']['Name'] == 'pending' or r['CurrentState']['Name'] == 'running':
            instance = module.instances.get(instance_id=r['InstanceId'])
            instance.running_state = 'pending'
            instance.service_status = 'not_ready'
            instance.save()
    print "before wait."
    print instance_ids
    result = wait(360, 30, all_instances_service_ok, InstanceIds)
    print "after wait."
    print result
    if not result:
        # TODO: handle exception
        raise Exception("Service failed to start")
        pass
    
    # return list of started instances:
    print "Instances: {0}".format(instance_ids)
    return instance_ids
    


def rollback_module(module, ec2client, elbclient=None):
    previous_module = module.previous_module

    # Start (power on) old version instances:
    poweron_module_aws(ec2client, previous_module)
    # Register old version instances with LB:
    lbreg_module_aws(elbclient, previous_module)
    # Deregister new version instances from LB:
    lbdereg_module_aws(elbclient, module)
    # Stop new version instances:
    stop_module_aws(module)


def remove_pid_and_exit(pidfile="/tmp/autoexec.pid", code=0):
    os.unlink(pidfile)
    sys.exit(code)


# write pid file:
PIDFILE = "/tmp/autoexec.pid"
with open(PIDFILE, 'w') as fp:
    pid = os.getpid()
    fp.write(str(pid))


# read update plan and step info:
try:
    plan_id = sys.argv[1]
    plan_id = int(plan_id)
except:
    print "Usage: python autoexec.py <updateplan_id>"
    remove_pid_and_exit()

plan = UpdatePlan.objects.get(pk=plan_id)
step = plan.get_current_step()
if step is None:
    print "Update plan has no available step. Nothing to do."
    remove_pid_and_exit()

module = step.module
previous_module = module.previous_module
session = module.profile.get_session(module.region)
ec2resource = session.resource('ec2')
ec2client = session.client('ec2')
elbclient = session.client('elb')

user = User.objects.get(username='System')


# START UPDATE STEP PROCEDURE:

# disable module alarms:
# disable_module_alarm(previous_module)


# deploy new version instances:
actionlog = UpdateActionLog.create_new_log(
    user=user,
    source_ip='127.0.0.1',
    update_plan=plan,
    update_step=step,
    action="start_module_aws"
)
try:
    result = start_module_aws(ec2resource, module)
except Exception as ex:
    actionlog.set_result(False, ex.message)
    actionlog.save()
    remove_pid_and_exit(code=1)
actionlog.set_result(True, "")
actionlog.save()


# register new:
actionlog = UpdateActionLog.create_new_log(
    user=user,
    source_ip='127.0.0.1',
    update_plan=plan,
    update_step=step,
    action="lbreg_module_aws"
)
try:
    result = lbreg_module_aws(elbclient, module)
except Exception as ex:
    actionlog.set_result(False, ex.message)
    actionlog.save()
    remove_pid_and_exit(code=1)
actionlog.set_result(True, "")
actionlog.save()


# deregister old:
actionlog = UpdateActionLog.create_new_log(
    user=user,
    source_ip='127.0.0.1',
    update_plan=plan,
    update_step=step,
    action='lbdereg_module_aws'
)
try:
    result = lbdereg_module_aws(elbclient, previous_module)
except Exception as ex:
    actionlog.set_result(False, ex.message)
    actionlog.save()
    remove_pid_and_exit(code=1)
actionlog.set_result(True, "")
actionlog.save()


# stop old version instances:
actionlog = UpdateActionLog.create_new_log(
    user=user,
    source_ip='127.0.0.1',
    update_plan=plan,
    update_step=step,
    action='stop_module_aws'
)
try:
    result = stop_module_aws(previous_module)
except Exception as ex:
    actionlog.set_result(False, ex.message)
    actionlog.save()
    remove_pid_and_exit(code=1)
actionlog.set_result(True, "")
actionlog.save()

if result:
    step.ec2_finished = True
    step.elb_finished = True
    step.finished = True
    step.save()
# if all steps are finished, mark UpdatePlan as finished:
plan_finished = True
for step in plan.steps.all():
    plan_finished = plan_finished and step.finished
if plan_finished:
    plan.finished = True
    plan.save()

# UPDATE STEP PROCEDURE FINISH

#rollback_module(module, ec2client, elbclient)
# poweron_module_aws(ec2client, previous_module)

remove_pid_and_exit(code=0)
