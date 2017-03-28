import json

import boto3
import pytz
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from awscredentialmgr.models import AWSProfile, AWSRegion
from awsresourcemgr.models import AWSResource
from boto3helper.ec2 import (get_instance_module_version,
                             get_instances_by_filters)
from boto3helper.tags import get_name, get_resource_name, to_dict
from ec2mgr.ec2 import add_instance_tags, add_volume_tags, run_instances
from ec2mgr.models import EC2Instance

from .models import Module, UpdateActionLog, UpdatePlan, UpdateStep

def JSONResponse(obj):
    return HttpResponse(json.dumps(obj), content_type="application/json")


@csrf_excempt
def new_updateplan(request):
    key = request.POST.get("key")
    if key:
        file_url = request.POST.get("file_url")
        file = s3_read(file_url)
    