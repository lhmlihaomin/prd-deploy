import datetime
import json
import traceback

import boto3
import pytz
from dateutil.parser import parse
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from authtoken.models import Token
from awscredentialmgr.models import AWSProfile, AWSRegion
from awsresourcemgr.models import AWSResource
from boto3helper.ec2 import (get_instance_module_version,
                             get_instances_by_filters)
from boto3helper.tags import get_name, get_resource_name, to_dict
from ec2mgr.ec2 import add_instance_tags, add_volume_tags, run_instances
from ec2mgr.models import EC2Instance

from .models import Module, UpdateActionLog, UpdatePlan, UpdateStep
from .views import make_new_version_module


def JSONResponse(obj):
    return HttpResponse(json.dumps(obj), content_type="application/json")


@csrf_exempt
def new_updateplan(request):
    print(request.is_ajax())
    #if not Token.auth(request):
    #    return HttpResponse("UnAuthorized.", status=403)
    try:
        data = json.loads(request.body)
        beta_version = data['beta_version']
        managers = data['managers'],
        data['update_steps']
    except TypeError, ValueError:
        return JsonResponse({"message": "Failed to decode JSON string."}, status=400)
    except KeyError:
        return JsonResponse({"message": "Key not found."}, status=400)

    try:
        with transaction.atomic():
            tz = pytz.timezone(settings.TIME_ZONE)
            timestamp_now = tz.localize(datetime.datetime.now())
            update_steps = []
            # create update plan:
            plan = UpdatePlan(
                project_name=data['project_name'] if data.has_key('project_name') else "<Unknown project_name>",
                project_code = data['project_code'] if data.has_key('project_code') else "<Unknown project_code>",
                project_leader = ", ".join(data['managers']),
                note = "",
                start_time=timestamp_now
            )
            plan.save()
            for i, update_step in enumerate(data['update_steps']):
                region = AWSRegion.objects.get(name=update_step['region'])
                profile = region.profiles.all()[0]
                load_balancer_names = None
                if update_step.has_key('load_balancer_names'):
                    load_balancer_names = update_step['load_balancer_names']
                count = None
                if update_step.has_key('count'):
                    count = update_step['count']
                # create or get new version module:
                module = make_new_version_module(
                    profile,
                    region,
                    update_step['module'],
                    update_step['current_version'],
                    update_step['update_version'],
                    instance_count=count,
                    load_balancer_names=load_balancer_names
                )
                # additional changes:
                if update_step.has_key('config'):
                    launch_conf = json.loads(module.configuration)
                    for key in update_step['config']:
                        if launch_conf.has_key(key):
                            launch_conf.update({key: update_step['config'][key]})
                    module.configuration = json.dumps(launch_conf, indent=2)
                module.save()
                # create step:
                step = UpdateStep(
                    sequence=i,
                    module=module,
                    start_time=parse(update_step['update_time']),
                )
                step.save()
                plan.steps.add(step)
            #raise Exception("Roll the hell back.")
    except Exception as ex:
        return HttpResponse(traceback.format_exc(), status=500)
    return JsonResponse({"message": "OK"})

 
@csrf_exempt
def atomic_test(request):
    try:
        with transaction.atomic():
            profile = AWSProfile.objects.all()[0]
            region = profile.regions.all()[0]
            module = Module(
                name="atomictest",
                profile=profile,
                region=region,
                current_version="1.1.1",
                previous_version="1.0.0",
                is_online_version=True,
                instance_count=1,
                configuration="",
                load_balancer_names="",
                service_type="java"
            )
            module.save()
            raise Exception("Test Exception")
            module = Module(
                name="atomictest1",
                profile=profile,
                region=region,
                current_version="1.1.1",
                previous_version="1.0.0",
                is_online_version=True,
                instance_count=1,
                configuration="",
                load_balancer_names="",
                service_type="java"
            )
            module.save()
    except Exception as ex:            
        return HttpResponse(ex.message)
            
    return HttpResponse("Atomic Test.")
