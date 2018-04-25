import os
import json
from datetime import datetime
import logging
import subprocess

from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings
import pytz
import boto3

from awscredentialmgr.models import AWSProfile, AWSRegion
from awsresourcemgr.models import AWSResource
from .models import Module, UpdatePlan, UpdateStep, UpdateActionLog
from boto3helper.ec2 import get_instances_by_filters, \
    get_instance_module_version
from boto3helper.tags import to_dict, get_name, get_resource_name
from ec2mgr.ec2 import run_instances, add_instance_tags, add_volume_tags
from ec2mgr.models import EC2Instance
from openfalcon import openfalcon_login, openfalcon_logout, openfalcon_disable

logger = logging.getLogger('common')

def JSONResponse(obj, status=200):
    return HttpResponse(json.dumps(obj), content_type="application/json", status=status)


@login_required
def run_module_ec2(request):
    """
    Run EC2 instances for an UpdateStep. The number of instances to run is
    determined by (instance_count - healthy_instance_count) of that
    module in the step.
    """
    # read request and models:
    step = get_object_or_404(UpdateStep, pk=request.POST.get('step_id'))
    # record action log:
    actionlog = UpdateActionLog.create(
        request,
        update_plan = step.update_plan.first(),
        update_step = step,
        action = "run_module_ec2"
    )
    if step.finished:
        actionlog.set_result(False, "Step already finished.")
        actionlog.save()
        return JSONResponse(False)
    module = step.module
    # boto3 session:
    session = module.profile.get_session(module.region)
    ec2res = session.resource('ec2')
    # boto3 throws errors if instance_count is 0, so intercept it here:
    if module.launch_count == 0:
        actionlog.set_result(False, "Launch number is 0.")
        actionlog.save()
        return JSONResponse([])
    # run instances:
    try:
        instance_ids = []
        instances = run_instances(ec2res, module, module.launch_count)
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
    except Exception as ex:
        actionlog.set_result(False, ex.message)
        actionlog.save()
        return HttpResponse(ex.message, status=500)
    actionlog.set_result(True, instance_ids)
    actionlog.save()
    return JSONResponse(instance_ids)


@login_required
def add_module_ec2_tags(request):
    step = get_object_or_404(UpdateStep, pk=request.POST.get('step_id'))
    # record action log:
    actionlog = UpdateActionLog.create(
        request,
        step.update_plan.first(),
        step,
        "add_module_ec2_tags"
    )
    if step.finished:
        actionlog.set_result(False, "Step already finished.")
        actionlog.save()
        return JSONResponse(False)
    module = step.module
    instance_ids = request.POST.getlist('instance_ids[]')
    if len(instance_ids) == 0:
        actionlog.set_result(False, "No instances to add tags to.")
        actionlog.save()
        return JSONResponse("No Instance ID.")
    session = module.profile.get_session(module.region)
    ec2res = session.resource('ec2')

    try:
        result = add_instance_tags(ec2res, module, instance_ids)
        for instance_id in result:
            if result[instance_id]:
                ec2instance = EC2Instance.objects.get(instance_id=instance_id)
                ec2instance.instance_tags_added = True
                ec2instance.name = result[instance_id]
                ec2instance.save()
    except Exception as ex:
        actionlog.set_result(False, ex.message)
        actionlog.save()
        return HttpResponse(ex.message, status=500)
    actionlog.set_result(True, result)
    actionlog.save()
    return JSONResponse(result)



@login_required
def add_module_volume_tags(request):
    step = get_object_or_404(UpdateStep, pk=request.POST.get('step_id'))
    # record action log:
    actionlog = UpdateActionLog.create(
        request,
        step.update_plan.first(),
        step,
        "add_module_volume_tags"
    )
    if step.finished:
        actionlog.set_result(False, "Step already finished.")
        actionlog.save()
        return JSONResponse(False)
    module = step.module
    instance_ids = request.POST.getlist('instance_ids[]')
    if len(instance_ids) == 0:
        actionlog.set_result(False, "No instances to add tags to.")
        actionlog.save()
        return JSONResponse("No Instance ID.")
    session = module.profile.get_session(module.region)
    ec2res = session.resource('ec2')

    try:
        result = add_volume_tags(ec2res, instance_ids)
        for instance_id in result:
            if result[instance_id]:
                ec2instance = EC2Instance.objects.get(instance_id=instance_id)
                ec2instance.volume_tags_added = True
                ec2instance.save()
    except Exception as ex:
        actionlog.set_result(False, ex.message)
        actionlog.save()
        return HttpResponse(ex.message, status=500)
    actionlog.set_result(True, result)
    actionlog.save()
    return JSONResponse(result)


def stop_module_ec2_instances(ec2res, module):
    ret = {}
    for ec2instance in module.instances.all():
        instance = ec2res.Instance(ec2instance.instance_id)
        try:
            result = instance.stop()
            running_state = result['StoppingInstances'][0]['CurrentState']['Name']
            ret.update({instance.id: running_state})
            ec2instance.running_state = running_state
            ec2instance.service_status = "down"
            ec2instance.note = "Instance not running"
            ec2instance.save()
        except Exception as ex:
            ret.update({instance.id: 'error'})
    return ret


@login_required
def stop_module_ec2(request):
    step = get_object_or_404(UpdateStep, pk=request.POST.get('step_id'))
    actionlog = UpdateActionLog.create(
        request,
        update_plan = step.update_plan.first(),
        update_step = step,
        action = "stop_module_ec2"
    )
    if step.finished:
        actionlog.set_result(False, "Step already finished.")
        actionlog.save()
        return JSONResponse(False)
    module = step.module
    #module = get_object_or_404(Module, pk=request.POST.get('module_id'))
    session = module.profile.get_session(module.region)
    ec2res = session.resource('ec2')

    #ret = stop_module_ec2_instances(ec2res, module)
    ret = module.mark_instances_for_stopping()
    actionlog.set_result(True, instance_ids)
    actionlog.save()
    return JSONResponse(ret)


@login_required
def stop_module_previous_ec2(request):
    step = get_object_or_404(UpdateStep, pk=request.POST.get('step_id'))
    #if step.finished:
    #    return JSONResponse(False)
    module = step.module
    module = module.previous_module
    instances = module.instances.all()
    # EC2Instance database ids:
    ids = [str(instance.id) for instance in instances]
    # Script path:
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
    subprocess.Popen(cmd)
    return JSONResponse(True)


@login_required
def reg_module_elb(request):
    step = get_object_or_404(UpdateStep, pk=request.POST.get('step_id'))
    actionlog = UpdateActionLog.create(
        request,
        update_plan = step.update_plan.first(),
        update_step = step,
        action = "reg_module_elb"
    )
    if step.finished:
        actionlog.set_result(False, "Step already finished.")
        actionlog.save()
        return JSONResponse(False)
    module = step.module
    session = module.profile.get_session(module.region)
    ec2res = session.resource('ec2')
    elbclient = session.client('elb')

    # Capital variables: boto3 naming style
    Instances = map(
        lambda x: {'InstanceId': x},
        [instance.instance_id for instance in module.instances.all()]
    )
    ret = {}
    for LoadBalancerName in module.load_balancer_names.split(','):
        LoadBalancerName = LoadBalancerName.strip()
        try:
            elbclient.register_instances_with_load_balancer(
                LoadBalancerName=LoadBalancerName,
                Instances=Instances
            )
            ret.update({LoadBalancerName: True})
        except Exception as ex:
            logger.error(ex.message)
            ret.update({LoadBalancerName: False})
    actionlog.set_result(True, ret)
    actionlog.save()
    return JSONResponse(ret)


@login_required
def dereg_module_elb(request):
    step = get_object_or_404(UpdateStep, pk=request.POST.get('step_id'))
    actionlog = UpdateActionLog.create(
        request,
        update_plan = step.update_plan.first(),
        update_step = step,
        action = "dereg_module_elb"
    )
    if step.finished:
        actionlog.set_result(False, "Step already finished.")
        actionlog.save()
        return JSONResponse(False)
    module = step.module.previous_module
    session = module.profile.get_session(module.region)
    ec2res = session.resource('ec2')
    elbclient = session.client('elb')

    Instances = map(
        lambda x: {'InstanceId': x},
        [instance.instance_id for instance in module.instances.all()]
    )
    ret = {}
    for LoadBalancerName in module.load_balancer_names.split(','):
        try:
            elbclient.deregister_instances_from_load_balancer(
                LoadBalancerName=LoadBalancerName,
                Instances=Instances
            )
            ret.update({LoadBalancerName: True})
        except Exception as ex:
            logger.error(ex.message)
            ret.update({LoadBalancerName: False})
    actionlog.set_result(True, ret)
    actionlog.save()
    return JSONResponse(ret)


@login_required
def finish_step(request):
    step = get_object_or_404(UpdateStep, pk=request.POST.get('step_id'))
    actionlog = UpdateActionLog.create(
        request,
        update_plan = step.update_plan.first(),
        update_step = step,
        action = "finish_step"
    )
    module = step.module
    if step.finished:
        actionlog.set_result(False, "Step already finished.")
        actionlog.save()
        return JSONResponse((False, "Step already finished."))
    result = step.check_finished()
    if not result[0]:
        actionlog.set_result(False, result[1])
        actionlog.save()
        return JSONResponse(result)
    step.set_finished()
    actionlog.set_result(True, "")
    actionlog.save()
    return JSONResponse((True, ""))


@login_required
def check_module_elb_health(request):
    step = get_object_or_404(UpdateStep, pk=request.POST.get('step_id'))
    if step.finished:
        return JSONResponse(False)
    module = step.module
    session = module.profile.get_session(module.region)
    ec2res = session.resource('ec2')
    elbclient = session.client('elb')

    Instances = list(map(lambda x:{'InstanceId':x.instance_id},module.instances.all()))
    healthy_count = 0
    for LoadBalancerName in module.load_balancer_names.split(','):
        try:
            InstanceStates = elbclient.describe_instance_health(
                LoadBalancerName=LoadBalancerName,
                Instances=Instances
            )
            InstanceStates = InstanceStates['InstanceStates']
            for InstanceState in InstanceStates:
                if InstanceState['State'] == 'InService':
                    healthy_count += 1
        except Exception as ex:
            logger.error(ex.message)
            return JSONResponse(False)
    return JSONResponse([healthy_count, module.instance_count])


@login_required
def disable_module_alarm(request):
    # Get instance list:
    step = get_object_or_404(UpdateStep, pk=request.POST.get('step_id'))
    module = step.module
    module = module.previous_module
    instances = module.instances.all()
    try:
        session = openfalcon_login(
            settings.OPENFALCON['login_url'],
            settings.OPENFALCON['username'],
            settings.OPENFALCON['password'],
            settings.OPENFALCON['cert_file'],
            settings.OPENFALCON['cert_key'],
            False
        )
    except:
        return JSONResponse({'message': 'openfalcon login failed'}, status=500)
    result = openfalcon_disable(
        session,
        settings.OPENFALCON['switch_url'],
        instances
    )
    if not result:
        return JSONResponse({'message': 'openfalcon disable failed'}, status=500)
    openfalcon_logout(
        session,
        settings.OPENFALCON['logout_url']
    )
    return JSONResponse({'result': 'OK'})
