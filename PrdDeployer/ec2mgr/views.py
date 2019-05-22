import json

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
import boto3

from awscredentialmgr.models import AWSProfile, AWSRegion
from updateplanmgr.models import Module
from ec2mgr.models import EC2Instance
from boto3helper.tags import get_resource_name
from boto3helper.ec2 import get_module_instances, get_instance_names

@login_required
def sync_instances(request, profile_name, region_name):
    profile = get_object_or_404(AWSProfile, name=profile_name)
    region = get_object_or_404(AWSRegion, name=region_name)
    boto3session = profile.get_session(region)
    ec2res = boto3session.resource('ec2')

    ret = []
    for module in Module.objects.filter(
            profile=profile,
            region=region):
        instances = get_module_instances(ec2res, module.name, module.version)
        names = get_instance_names(instances)
        for instance in instances:
            try:
                ec2instance = EC2Instance.objects.get(instance_id=instance.id)
                ec2instance.name = get_resource_name(instance)
                ec2instance.running_state = instance.state['Name']
                if ec2instance.running_state != "running":
                    ec2instance.service_status = "down"
                    ec2instance.note = "Instance not running."
                ec2instance.save()
            except:
                # instance doesn't exist:
                print("Adding instance %s to module %s"%(instance.id, module.display_name))
                ec2instance = EC2Instance()
                ec2instance.load_boto3_instance(instance)
                ec2instance.save()
                module.instances.add(ec2instance)

        #names = ['instance1', 'instance2']
        ret.append({
            'module': module.display_name,
            'instances': names
        })

    #return HttpResponse(json.dumps(ret, indent=2), content_type="application/json")
    return render(request, 'ec2mgr/sync_instances.html', {'ret': ret})


@login_required
def sync_instances_ex(request, profile_name, region_name):
    profile = get_object_or_404(AWSProfile, name=profile_name)
    region = get_object_or_404(AWSRegion, name=region_name)
    boto3session = profile.get_session(region)
    ec2res = boto3session.resource('ec2')
    # clear ec2instances that don't belong to any module:

    ret = []
    for module in Module.objects.filter(profile=profile,region=region):
        print(module.name+"-"+module.current_version)
        instances = get_module_instances(ec2res, module.name, module.version)
        names = get_instance_names(instances)
        for instance in instances:
            if instance.state['Name'] == 'running':
                #if not module.is_online_version:
                #    module.set_online_version()
                module.set_online_version()
            try:
                ec2instance = EC2Instance.objects.get(instance_id=instance.id)
                ec2instance.name = get_resource_name(instance)
                ec2instance.running_state = instance.state['Name']
                if ec2instance.running_state != "running":
                    ec2instance.service_status = "down"
                    ec2instance.note = "Instance not running."
                ec2instance.save()
            except:
                # instance doesn't exist:
                print("Adding instance %s to module %s"%(instance.id, module.display_name))
                ec2instance = EC2Instance()
                ec2instance.load_boto3_instance(instance)
                ec2instance.save()
                module.instances.add(ec2instance)
        ret.append({
            'module': module.display_name,
            'instances': names
        })

    return render(request, 'ec2mgr/sync_instances.html', {'ret': ret})


@login_required
def sync_vpc_ids(request):
    ids = {}
    for module in Module.objects.all():
        pid = module.profile.name
        rid = module.region.name
        if ids.has_key(pid):
            if ids[pid].has_key(rid):
                pass
            else:
                ids[pid].update({
                    rid: []
                })
        else:
            ids.update({
                pid: {
                    rid: []
                }
            })
        for instance in module.instances.all():
            #print("Appending %s to %s:%s"%(instance.instance_id, pid, rid))
            ids[pid][rid].append(instance.instance_id)

    for pid in ids.keys():
        for rid in ids[pid].keys():
            instance_ids = ids[pid][rid]
            if 'e' in locals():
                del e
            if 's' in locals():
                del s
            s = boto3.Session(profile_name=pid, region_name=rid)
            e = s.resource('ec2')
            #for instance in e.instances.filter(InstanceIds=instance_ids):
                #print(instance.vpc_id)
            for instance_id in instance_ids:
                try:
                    instance = e.Instance(instance_id)
                    vpc_id = instance.vpc_id
                    print(vpc_id)
                    ec2instance = EC2Instance.objects.get(instance_id=instance_id)
                    ec2instance.vpc_id = vpc_id
                    ec2instance.save()
                except Exception as ex:
                    print(ex.message)
                    #raise ex
                    #print("%s:%s Instance %s does not exist."%(pid, rid, instance_id))


@login_required
def instances(request):
    profile_name = request.GET.get('profile_name')
    region_name = request.GET.get('region_name')
    module_name = request.GET.get('module')
    online_version = request.GET.get('online')

    # handle form post if any:
    if request.method == "POST":
        ec2instance = get_object_or_404(EC2Instance, pk=request.POST.get('id'))
        if request.POST.get('running_state'):
            ec2instance.running_state = request.POST.get('running_state')
        if request.POST.get('service_status'):
            ec2instance.service_status = request.POST.get('service_status')
        if request.POST.get('note'):
            ec2instance.note = request.POST.get('note')
        ec2instance.save()

    if profile_name is None:
        return HttpResponse("No profile.")
    if region_name is None:
        return HttpResponse("No region.")
    if online_version is not None:
        online_version = (online_version.lower() == "true")
    print(repr(online_version))

    profile = AWSProfile.objects.get(name=profile_name)
    region = AWSRegion.objects.get(name=region_name)
    if module_name is None:
        modules = Module.objects.filter(
            profile=profile,
            region=region,
            is_online_version=online_version
        )
    else:
        modules = Module.objects.filter(
            profile=profile,
            region=region,
            name=module_name,
            is_online_version=online_version
        )
    module_names = []
    module_instances = []
    for module in modules:
        module_names.append(module.display_name)
        module_instances.append(module.instances)
    context = {
        'modules': modules,
        'module_names': module_names,
        'module_instances': module_instances
    }
    return render(request, 'ec2mgr/instances.html', context=context)


@login_required
def retired_instances(request):
    profiles = AWSProfile.objects.all()
    regions = AWSRegion.objects.all()

    # handle POST request:
    if 'terminate' in request.POST:
        ids = request.POST.getlist('id[]')
        instances = EC2Instance.objects.filter(pk__in=ids)
        for instance in instances:
            print("Terminating "+instance.name)
        # TODO: Terminate instances here.
        return HttpResponse("POSTed")

    # handle GET request:
    if 'profile_name' in request.GET:
        profile = get_object_or_404(AWSProfile, name=request.GET['profile_name'])
    else:
        profile = None
    if 'region_name' in request.GET:
        region = get_object_or_404(AWSRegion, name=request.GET['region_name'])
    else:
        region = None

    instances = []
    if not (profile is None or region is None):
        # search for retired instances:
        instances = EC2Instance.objects.filter(retired=True).exclude(running_state='terminated')

    context = {
        'title': 'Retired Instances',
        'profiles': profiles,
        'regions': regions,
        'instances': instances,
        'profile': profile,
        'region': region,
    }
    return render(request, 'ec2mgr/retired.html', context=context)