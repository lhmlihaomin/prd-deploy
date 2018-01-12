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
# REST framework:
from rest_framework import generics
from rest_framework import mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from awscredentialmgr.models import AWSProfile, AWSRegion
from awsresourcemgr.models import AWSResource
from boto3helper.ec2 import (get_instance_module_version,
                             get_instances_by_filters)
from boto3helper.tags import get_name, get_resource_name, to_dict
from ec2mgr.ec2 import add_instance_tags, add_volume_tags, run_instances
from ec2mgr.models import EC2Instance

from .models import Module, UpdateActionLog, UpdatePlan, UpdateStep
from .views import make_new_version_module


def token_auth(request):
    auth = TokenAuthentication()
    try:
        user, token = auth.authenticate(request)
    except:
        return None
    # Check permission if needed:
    pass
    return user


def image_exists(region, module, version):
    # Add dash to head & tail to avoid conflict like "mod1" with "smbMod1":
    # region = 
    image_name_filter = '-'.join(['', module, version, ''])
    queryset = AWSResource.objects.filter(
        region=region,
        resource_type='image',
        name__icontains=image_name_filter
    )
    return queryset.exists()

def fetch_new_image(region, module, version):
    # Connect to AWS:
    profile = region.profiles.all()[0]
    session = boto3.Session(profile_name=profile.name, region_name=region.name)
    ec2 = session.resource('ec2')
    # Filter image by keyword:
    ami_filter = 'preprd-ami-'+module+'-'+version+'-*'
    images = ec2.images.filter(Filters=[{'Name': 'name', 'Values': [ami_filter,]}])
    image_found = False
    for image in images:
        image_found = True
        break
    if image_found:
        # Check if image already exists:
        queryset = AWSResource.objects.filter(resource_id=image.id)
        if queryset.exists():
            return queryset.first()
        else:
            # Add image to database:
            awsresource = AWSResource(
                name=image.name,
                resource_id=image.id,
                resource_type='image',
                profile=profile,
                region=region
            )
            awsresource.save()
            return awsresource
    else:
        raise Exception("Image not found for "+module+'-'+version)



@csrf_exempt
def new_updateplan(request):
    # Authenticate token:
    user = token_auth(request)
    if user is None:
        return JsonResponse({"message": "Auth failed."}, status=401)
    # Parse POST data:
    try:
        data = json.loads(request.body)
        managers = data['managers'],
        data['update_steps']
    except (TypeError, ValueError):
        return JsonResponse({"message": "Failed to decode JSON string."}, status=400)
    except KeyError:
        return JsonResponse({"message": "Key not found."}, status=400)
    # Check if all images can be found in our database:
    try:
        for update_step in data['update_steps']:
            region_name = update_step['region']
            module = update_step['module']
            current_version = update_step['current_version']
            update_version = update_step['update_version']

            region = AWSRegion.objects.get(name=region_name)    
            if not image_exists(region, module, current_version):
                image = fetch_new_image(region, module, current_version)
            if not image_exists(region, module, update_version):
                image = fetch_new_image(region, module, update_version)
    except Exception as ex:
        return JsonResponse({"message": ex.message}, status=400)


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
            # endfor
        # endwith
            #raise Exception("Roll the hell back.")
    except Exception as ex:
        return HttpResponse(traceback.format_exc(), status=500)
    return JsonResponse({"updateplan_id": plan.id})
    #return JsonResponse({"message": "OK"})


class NewUpdatePlanMixin(mixins.CreateModelMixin, generics.GenericAPIView):
    authentication_classes = [TokenAuthentication,]
    permission_classes = [IsAuthenticated]
