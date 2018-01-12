import json
from datetime import datetime
import logging

from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import pytz
import boto3

from awscredentialmgr.models import AWSProfile, AWSRegion
from awsresourcemgr.models import AWSResource
from ec2mgr.models import EC2Instance
from .models import Module, UpdatePlan, UpdateStep, UpdateActionLog
from boto3helper.ec2 import get_instances_by_filters, \
    get_instance_module_version
from boto3helper.tags import to_dict, get_name, get_resource_name

logger = logging.getLogger('common')


@login_required
def index(request):
    profiles = AWSProfile.objects.all()
    context = {
        'title': "Home",
        'profiles': profiles
    }
    return render(request, 'updateplanmgr/index_ace.html', context=context)


@login_required
def modules(request, profile_name, region_name):
    profile = get_object_or_404(AWSProfile, name=profile_name)
    region = get_object_or_404(AWSRegion, name=region_name)
    logger.info("I'm entering!")

    modules = Module.objects.filter(profile=profile, region=region)\
        .order_by("name", "-current_version")

    context = {
        'title': "Modules",
        'profile': profile,
        'region': region,
        'modules': modules
    }
    return render(request, 'updateplanmgr/modules_ace.html', context)


@login_required
def edit_module_json(request, module_id):
    module = Module.objects.get(pk=module_id)
    if request.method == "POST":
        action = request.POST.get('submit')
        if action == "Reset":
            return HttpResponseRedirect(reverse('updateplanmgr:edit_module_json', args=(module.id,)))
        elif action == "Cancel":
            return HttpResponseRedirect(reverse(
                'updateplanmgr:modules',
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
                    'updateplanmgr:modules',
                    kwargs={
                        'profile_name': module.profile.name,
                        'region_name': module.region.name
                    }
                ))
            except:
                context = {
                    'title': "Edit Module",
                    'message': 'Bad JSON text.',
                    'module': module,
                    'json': text
                }
                return render(request, 'updateplanmgr/edit_module_json_ace.html', context)
    else:
        context = {
            'title': "Edit Module",
            'module': module,
            'json': module.configuration
        }
        return render(request, 'updateplanmgr/edit_module_json_ace.html', context)


@login_required
def updateplans(request):
    plans = UpdatePlan.objects.all()
    context = {
        'title': "Update Plans",
        'plans': plans
    }
    return render(request, 'updateplanmgr/updateplans_ace.html', context)


@login_required
def updateplan(request, plan_id):
    plan = get_object_or_404(UpdatePlan, pk=plan_id)
    steps = plan.steps.order_by('sequence')
    context = {
        'title': "UpdatePlan",
        'plan': plan,
        'steps': steps
    }
    return render(request, 'updateplanmgr/updateplan_ace.html', context)


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
        raise Exception("ImageNotFound: %s:%s, %s-%s"%(profile.name, region.name, module_name, new_version))
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
        # set new count when scaling out/in:
        if module.instance_count != instance_count and instance_count != 0:
            module.instance_count = instance_count
        module.save()
        return module
    except:
        # create new module:
        ## copy unchanged info from old module:
        module = Module(
            name=module_old.name,
            profile=module_old.profile,
            region=module_old.region,
            current_version=new_version,
            previous_version=module_old.current_version,
            service_type=module_old.service_type
        )
        # edit new values:
        if instance_count is None:
            module.instance_count = module_old.instance_count
        elif instance_count == 0:
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
    """Create a new update plan"""
    if request.method =="POST":
        # record action log:
        actionlog = UpdateActionLog.create(
            request,
            action="new_updateplan"
        )
        # create plan:
        str_start_time = request.POST.get('start_time')
        tz = pytz.timezone(settings.TIME_ZONE)
        start_time = tz.localize(datetime.now())
        # try different formats of datetime:
        formats = (
            "%Y-%m-%d %H:%M:%S",
            "%Y%m%d%H%M%S",
            "%Y%m%d"
        )
        for fmt in formats:
            try:
                parsed_start_time = datetime.strptime(str_start_time, fmt)
                parsed_start_time = tz.localize(parsed_start_time)
                start_time = parsed_start_time
                break
            except:
                continue
        plan = UpdatePlan(
            project_name=request.POST.get('project_name'),
            project_code=request.POST.get('project_code'),
            project_leader=request.POST.get('project_leader'),
            note=request.POST.get('note'),
            start_time=start_time
        )
        plan.save()
        # update action log:
        actionlog.update_plan = plan
        actionlog.set_result(True)
        actionlog.save()
        # create each step and add to plan:
        stepCount = int(request.POST.get('stepCount'))
        for i in range(stepCount):
            profile_name = request.POST.get('profile['+str(i)+']')
            region_name = request.POST.get('region['+str(i)+']')
            instance_count = request.POST.get('numberOfInstances['+str(i)+']')
            try:
                instance_count = int(instance_count)
            except:
                instance_count = 0
            module = make_new_version_module(
                AWSProfile.objects.get(name=profile_name),
                AWSRegion.objects.get(name=region_name),
                request.POST.get('module['+str(i)+']'),
                request.POST.get('currentVersion['+str(i)+']'),
                request.POST.get('newVersion['+str(i)+']'),
                instance_count
            )
            module.save()
            step = UpdateStep(
                sequence=i,
                module=module,
                start_time=timezone.now()
            )
            step.save()
            plan.steps.add(step)
        return HttpResponseRedirect(reverse('updateplanmgr:updateplan', args=(plan.id,)))
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
                #for module in Module.objects\
                #    .filter(profile=awsprofile, region=awsregion)\
                #    .order_by('name', '-current_version'):
                for module in Module.objects\
                    .filter(profile=awsprofile, region=awsregion)\
                    .order_by('name', '-id'):
                    modules[module_key].append(module.to_dict())


        context = {
            'title': "New Updateplan",
            'awsprofiles_json': json.dumps(awsprofiles),
            'awsregions_json': json.dumps(awsregions),
            'modules_json': json.dumps(modules, indent=2),
        }
        return render(request, "updateplanmgr/new_updateplan_ace.html", context)


@login_required
def new_module(request):
    if request.method == "POST":
        # record action log:
        actionlog = UpdateActionLog.create(
            request,
            action="new_module"
        )
        # get form data:
        name = request.POST.get("name")
        profile_name = request.POST.get("profile_name")
        profile = AWSProfile.objects.get(name=profile_name)
        region_name = request.POST.get("region_name")
        region = AWSRegion.objects.get(name=region_name)

        current_version = request.POST.get("current_version")
        previous_version = request.POST.get("previous_version")

        instance_count = int(request.POST.get("instance_count"))
        configuration = request.POST.get("configuration")
        load_balancer_names = request.POST.get("load_balancer_names")
        service_type = request.POST.get("service_type")
        # see if it's already there:
        if Module.objects.filter(
            profile=profile,
            region=region,
            name=name,
            current_version=current_version
        ).count() > 0:
            return HttpResponse("Module already exists.")
        # create module:
        try:
            obj = json.loads(configuration)
        except:
            return HttpResponse("Bad JSON.")
        module = Module(
            name=name,
            profile=profile,
            region=region,
            current_version=current_version,
            previous_version=previous_version,
            instance_count=instance_count,
            configuration=json.dumps(obj, indent=2),
            load_balancer_names=load_balancer_names,
            service_type=service_type
        )
        module.save()
        module.set_online_version()
        module.save()
        # update action log:
        actionlog.set_result(True, "created module %d"%(module.id,))
        actionlog.save()
        return HttpResponseRedirect(reverse('updateplanmgr:modules', kwargs={'profile_name': profile_name, 'region_name': region_name}))

    profiles = AWSProfile.objects.all()
    regions = AWSRegion.objects.all()
    context = {
        'title': "New Module",
        'profiles': profiles,
        'regions': regions,
    }
    return render(request, 'updateplanmgr/new_module_ace.html', context)


@login_required
def fix_service_types(request):
    ret = ""
    service_types = settings.SERVICE_TYPES
    for module in Module.objects.all():
        if service_types.has_key(module.name):
            if module.service_type != service_types[module.name]:
                ret += "%s: %s - %s<br/>\r\n"%(module.name, module.service_type, service_types[module.name])
                module.service_type = service_types[module.name]
                module.save()
        else:
            ret += "%s: service type not found.<br/>\r\n"%(module.name,)
            module.service_type = ""
            module.save()
    return HttpResponse(ret)


@login_required
def instances_summary(request, plan_id):
    """list all instances relevant to this updateplan."""
    plan = get_object_or_404(UpdatePlan, pk=plan_id)
    steps = plan.steps.order_by('sequence')
    context = {
        'title': "Instances Summary",
        'plan': plan,
        'steps': []
    }
    for step in steps:
        module = step.module
        module_name = module.display_name
        prev_module = module.previous_module
        instances = module.instances.all()
        if prev_module is None:
            prev_module_name = ""
            prev_instances = []
        else:
            prev_module_name = prev_module.display_name
            prev_instances = prev_module.instances.all()
        context['steps'].append({
            'sequence': step.sequence,
            'module_name': module_name,
            'prev_module_name': prev_module_name,
            'instances': instances,
            'prev_instances': prev_instances
        })
    return render(request, 'updateplanmgr/instances_summary_ace.html', context=context)


@login_required
def elb_summary(request, plan_id):
    """List relevant ELB service status."""
    plan = get_object_or_404(UpdatePlan, pk=plan_id)
    steps = plan.steps.order_by('sequence')
    context = {
        'title': "ELB Summary",
        'plan': plan,
        'elb_states': []
    }
    elb_states = []
    for step in steps:
        module = step.module
        module_name = module.display_name
        module_elb_names = [
            x.strip() for x in module.load_balancer_names.split(",")
        ]
        if module_elb_names[0] != "":
            s = module.profile.get_session(module.region)
            c = s.client('elb')
            for elb_name in module_elb_names:
                instance_states = []
                resp = c.describe_instance_health(LoadBalancerName=elb_name)
                for instance_health in resp['InstanceStates']:
                    instance_id = instance_health['InstanceId']
                    state = instance_health['State']
                    try:
                        ec2instance = EC2Instance.objects.get(instance_id=instance_id)
                        instance_name = ec2instance.name
                    except:
                        instance_name = ""
                    instance_states.append({
                        'instance_id': instance_id,
                        'instance_name': instance_name,
                        'state': state,
                    })
                elb_states.append({
                    'elb_name': elb_name,
                    'instance_states': instance_states
                })
    context['elb_states'] = elb_states
    return render(request, 'updateplanmgr/elb_summary_ace.html', context=context)


@login_required
def actionlogs(request, plan_id):
    plan = get_object_or_404(UpdatePlan, pk=plan_id)
    steps = plan.steps.order_by('sequence')
    logs = []
    actionlogs = UpdateActionLog.objects.filter(
        update_plan = plan,
        update_step__isnull=True
    )
    logs.append([-1, "", actionlogs])
    for step in steps:
        actionlogs = UpdateActionLog.objects.filter(
            update_plan = plan,
            update_step = step
        )
        logs.append([step.sequence, step.module.__unicode__(), actionlogs])
    context = {
        'title': "Action Logs",
        'plan': plan,
        'logs': logs
    }
    return render(request, 'updateplanmgr/actionlogs_ace.html', context=context)

    
@login_required
def edit_module(request, module_id):
    # Read module info:
    module = Module.objects.get(pk=module_id)

    context = {}
    if request.method == "GET":
        # Fill context:
        context = {
            'title': "Edit Module",
            'name': module.name,
            'instance_count': module.instance_count,
            'configuration': module.configuration,
            'load_balancer_names': module.load_balancer_names,
            'service_type': module.service_type,
            'module': module,
        }

        # Render page:
        return render(request, 'updateplanmgr/edit_module_ace.html', context=context)
    elif request.method == "POST":
        # Read post form & compare args:
        errors = []
        if request.POST.get('name'):
            name = request.POST.get('name')
            if name != module.name:
                module.name = name
        if request.POST.get('instance_count'):
            instance_count = int(request.POST.get('instance_count'))
            if instance_count != module.instance_count:
                module.instance_count = instance_count
        if request.POST.get('load_balancer_names'):
            print request.POST.get('load_balancer_names')
            load_balancer_names = request.POST.get('load_balancer_names')
            if load_balancer_names != module.load_balancer_names:
                print "editing load balancer names..."
                module.load_balancer_names = load_balancer_names
        if request.POST.get('service_type'):
            service_type = request.POST.get('service_type')
            if service_type != module.service_type:
                module.service_type = service_type
        if request.POST.get('configuration'):
            try:
                configuration = json.loads(request.POST.get('configuration'))
                configuration = json.dumps(configuration, indent=2)
                module.configuration = configuration
            except:
                errors.append("Configuration is not valid JSON")

        # Save module
        if not errors:
            print "Saving module ..."
            module.save()
            return HttpResponseRedirect(
                reverse(
                    'updateplanmgr:modules',
                    kwargs={
                        'profile_name': module.profile.name,
                        'region_name': module.region.name,
                    }
                )
            )
        else:
            print errors
            module.refresh_from_db()

        context = {
            'title': "Edit Module",
            'name': module.name,
            'instance_count': module.instance_count,
            'configuration': module.configuration,
            'load_balancer_names': module.load_balancer_names,
            'service_type': module.service_type,
            'module': module,
            'post': request.POST,
            'errors': errors,
        }
        # Render page:
        return render(request, 'updateplanmgr/edit_module_ace.html', context=context)
