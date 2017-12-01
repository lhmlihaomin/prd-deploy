from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from awscredentialmgr.models import AWSProfile, AWSRegion
from awsresourcemgr.models import AWSResource, AWSResourceHandler

def update_resources(request, profile_name, region_name, resource_type):
    """Update online AWS resources."""
    profile = get_object_or_404(AWSProfile, name=profile_name)
    region = get_object_or_404(AWSRegion, name=region_name)
    session = profile.get_session(region)
    arh = AWSResourceHandler(profile.account_id, session)

    resource_types = (
        "vpcs",
        "images",
        "key_pairs",
        "instance_profiles",
        "subnets",
        "security_groups",
        "server_certificates",
    )
    resource_type_names = {
        "vpcs": "vpc",
        "images": "image",
        "key_pairs": "key_pair",
        "instance_profiles": "instance_profile",
        "subnets": "subnet",
        "security_groups": "security_group",
        "server_certificates": "server_certificate",
    }

    ret = []

    if resource_type == "all":
        resource_types_to_update = resource_types
    else:
        if resource_type not in resource_types:
            return HttpResponse("Unknown resource type: %s"%(resource_type,), status=400)
        resource_types_to_update = (resource_type,)

    for resource_type in resource_types_to_update:
        # look for "update_xxx" method in AWSResourceHandler object:
        func = getattr(arh, "update_"+resource_type)
        # make request:
        resources = func()
        # get a dict indexed by resource_id:
        resource_dict = {}
        for resource in resources:
            resource_dict.update({
                resource[1]: resource
            })
        # get online resource ids:
        resource_ids = [x[1] for x in resources]
        # get db resource ids:
        awsresource_ids = AWSResource.objects\
                        .values_list("resource_id", flat=True)\
                        .filter(profile=profile, region=region, resource_type=resource_type_names[resource_type])
        awsresource_ids = list(awsresource_ids)
        # compare local resources and online resources,
        # add "not-found-in-local" and delete "only-found-in-local":
        ids_to_add = list(set(resource_ids) - set(awsresource_ids))
        ids_to_del = list(set(awsresource_ids) - set(resource_ids))

        # add new awsresources:
        for resource_id in ids_to_add:
            resource = resource_dict[resource_id]
            awsresource = AWSResource(
                profile=profile,
                region=region,
                name=resource[0],
                resource_id=resource[1],
                resource_type=resource[2],
                arn=resource[3],
                parent=None
            )
            if resource_type != "vpc" and resource[4] is not None:
                try:
                    awsresource.parent = AWSResource.objects.get(resource_type="vpc", resource_id=resource[4])
                except Exception as ex:
                    print(str(resource))
                    raise ex
            awsresource.save()
        # delete missing awsresources:
        for resource_id in ids_to_del:
            awsresource = AWSResource.objects.get(profile=profile, region=region, resource_id=resource_id)
            awsresource.delete()

        ret.append([resource_type, str(ids_to_add), str(ids_to_del)])
        title = "Update Resources"
    return render(request, "awsresourcemgr/update_resources_ace.html", locals())


@login_required
def resources(request, profile_name, region_name):
    resource_types = (
        "image",
        "vpc",
        "key_pair",
        "instance_profile",
        "subnet",
        "security_group",
        "server_certificate",
    )
    profile = AWSProfile.objects.get(name=profile_name)
    region = AWSRegion.objects.get(name=region_name)
    context = {}
    resource_arr = []
    for resource_type in resource_types:
        resources = AWSResource.objects.filter(
            profile=profile,
            region=region,
            resource_type=resource_type
        ).order_by('name')
        resource_arr.append(
            [
                resource_type,
                [(resource.name, resource.resource_id) for resource in resources]
            ]
        )
    context = {
        'title': "Resources", 
        'profile': profile,
        'region': region,
        'resource_arr': resource_arr
    }
    return render(request, 'awsresourcemgr/resources_ace.html', context)
