import json
from datetime import datetime
import logging

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
from .models import Module, UpdatePlan, UpdateStep
from boto3helper.ec2 import get_instances_by_filters, \
    get_instance_module_version
from boto3helper.tags import to_dict, get_name, get_resource_name

logger = logging.getLogger('common')

@login_required
def modules(request, profile_name, region_name):
    profile = get_object_or_404(AWSProfile, name=profile_name)
    region = get_object_or_404(AWSRegion, name=region_name)
    logger.info("I'm entering!")

    modules = Module.objects.filter(profile=profile, region=region)\
        .order_by("name", "-current_version")
    
    context = {
        'profile': profile,
        'region': region,
        'modules': modules
    }
    return render(request, 'updateplanmgr/modules.html', context)


@login_required
def edit_module_json(request, module_id):
    module = Module.objects.get(pk=module_id)
    if request.method == "POST":
        action = request.POST.get('submit')
        if action == "Reset":
            return HttpResponseRedirect(reverse('edit_module_json', args=(module.id,)))
        elif action == "Cancel":
            return HttpResponseRedirect(reverse(
                'modules',
                kwargs={
                    'profile_name': module.profile.name,
                    'region_name': module.region.name
                }
            ))
        elif action == "Save":
            text = request.POST.get('json')
            try:
                obj = json.loads(text)
                module.configuration = json.dumps(obj, indent=2)
                module.save()
                return HttpResponseRedirect(reverse(
                    'modules',
                    kwargs={
                        'profile_name': module.profile.name,
                        'region_name': module.region.name
                    }
                ))
            except:
                context = {
                    'message': 'Bad JSON text.',
                    'module': module,
                    'json': text
                }
                return render(request, 'updateplanmgr/edit_module_json.html', context)
    else:
        context = {
            'module': module,
            'json': module.configuration
        }
        return render(request, 'updateplanmgr/edit_module_json.html', context)


@login_required
def updateplans(request):
    pass


@login_required
def updateplan(request, plan_id):
    plan = get_object_or_404(UpdatePlan, pk=plan_id)
    steps = plan.steps.order_by('sequence')
    context = {
        'plan': plan,
        'steps': steps
    }
    return render(request, 'updateplanmgr/updateplan.html', context)


def get_module_image(profile, region, module_name, version):
    """Get module AMI by module name and version"""
    image = AWSResource.objects.get(
        profile=profile,
        region=region,
        resource_type="image",
        name__contains="-%s-%s-"%(module_name, version)
    )
    return image


def make_new_version_module(profile, region, module_name, current_version, \
    new_version, instance_count=None, load_balancer_names=None):
    # check for new image:
    try:
        new_image = get_module_image(profile, region, module_name, new_version)
    except:
        raise Exception("ImageNotFound")
    # check for old module:
    try:
        module_old = Module.objects.get(
            profile=profile,
            region=region,
            name=module_name,
            current_version=current_version
        )
    except:
        raise Exception("OldModuleNotFound")
    # check if new version module already exists:
    try:
        module = Module.objects.get(
            profile=profile,
            region=region,
            name=module_name,
            current_version=new_version
        )
        return module
    except:
        # create new module:
        ## copy unchanged info from old module:
        module = Module(
            name=module_old.name,
            profile=module_old.profile,
            region=module_old.region,
            current_version=new_version,
            previous_version=module_old.current_version
        )
        # edit new values:
        if instance_count is None:
            module.instance_count = module_old.instance_count
        else:
            module.instance_count = instance_count
        if load_balancer_names is None:
            module.load_balancer_names = module_old.load_balancer_names
        else:
            module.load_balancer_names = load_balancer_names
        # set new image in module configuration:
        conf = json.loads(module_old.configuration)
        conf.update({
            'image':[new_image.name, new_image.resource_id]
        })
        module.configuration = json.dumps(conf, indent=2)
        module.save()
        return module

def make_update_step():
    pass

@login_required
def new_updateplan(request):
    if request.method =="POST":
        # create plan:
        start_time = request.POST.get('start_time')
        fmt = "%Y-%m-%d %H:%M:%S"
        start_time = datetime.strptime(start_time, fmt)
        tz = pytz.timezone(settings.TIME_ZONE)
        start_time = tz.localize(start_time)
        plan = UpdatePlan(
            project_name=request.POST.get('project_name'),
            project_code=request.POST.get('project_code'),
            project_leader=request.POST.get('project_leader'),
            start_time=start_time
        )
        plan.save()
        # create each step and add to plan:
        stepCount = int(request.POST.get('stepCount'))
        for i in range(stepCount):
            profile_name = request.POST.get('profile['+str(i)+']')
            region_name = request.POST.get('region['+str(i)+']')
            module = make_new_version_module(
                AWSProfile.objects.get(name=profile_name),
                AWSRegion.objects.get(name=region_name),
                request.POST.get('module['+str(i)+']'),
                request.POST.get('currentVersion['+str(i)+']'),
                request.POST.get('newVersion['+str(i)+']'),
                int(request.POST.get('numberOfInstances['+str(i)+']'))
            )
            module.save()
            step = UpdateStep(
                sequence=i,
                module=module,
                start_time=timezone.now()
            )
            step.save()
            plan.steps.add(step)
        return HttpResponseRedirect(reverse('updateplan', args=(plan.id,)))
        return HttpResponse(
            json.dumps(request.POST, indent=2),
            content_type="application/json"
        )
    else:
        awsprofiles = []
        awsregions = {}
        modules = {}
        for awsprofile in AWSProfile.objects.all().order_by('name'):
            awsprofiles.append(awsprofile.name)
            awsregions.update({
                awsprofile.name: []
            })
            for awsregion in awsprofile.regions.all().order_by('name'):
                awsregions[awsprofile.name].append(awsregion.name)
                module_key = awsprofile.name+":"+awsregion.name
                modules.update({
                    module_key: []
                })
                for module in Module.objects\
                    .filter(profile=awsprofile, region=awsregion)\
                    .order_by('name', '-current_version'):
                    modules[module_key].append(module.to_dict())


        context = {
            'awsprofiles_json': json.dumps(awsprofiles),
            'awsregions_json': json.dumps(awsregions),
            'modules_json': json.dumps(modules, indent=2),
        }
        return render(request, "updateplanmgr/new_updateplan.html", context)


def v1(request):
    profile = get_object_or_404(AWSProfile, name='cn-alpha')
    region = get_object_or_404(AWSRegion, name='cn-north-1')
    module_name = "mod1"
    current_version = "1.0.0"
    new_version = "1.1.1"
    module = make_new_version_module(profile, region, module_name, current_version, new_version)
    return HttpResponse(module.display_name)
