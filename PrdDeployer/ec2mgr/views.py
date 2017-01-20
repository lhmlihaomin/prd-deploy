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
    # TODO

    ret = []
    for module in Module.objects.filter(profile=profile,region=region):
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
                #print instance.vpc_id
            for instance_id in instance_ids:
                try:
                    instance = e.Instance(instance_id)
                    vpc_id = instance.vpc_id
                    print vpc_id
                    ec2instance = EC2Instance.objects.get(instance_id=instance_id)
                    ec2instance.vpc_id = vpc_id
                    ec2instance.save()
                except Exception as ex:
                    print ex.message
                    #raise ex
                    #print("%s:%s Instance %s does not exist."%(pid, rid, instance_id))
