from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse

from awscredentialmgr.models import AWSProfile, AWSRegion
from awsresourcemgr.models import AWSResource, AWSResourceHandler

def update_resources(request, profile_name, region_name):
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
    for resource_type in resource_types:
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
    return render(request, "awsresourcemgr/update_resources.html", locals())

