"""
Install some sample models.
"""

import os
import sys
import django
import datetime

# Initialize django environment:
sys.path.append(os.path.abspath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'PrdDeployer.settings'
django.setup()

from awscredentialmgr.models import AWSRegion, AWSProfile
from updateplanmgr.models import Module, UpdatePlan, UpdateStep

# Default values:
AWS_REGIONS = {
    "cn-north-1": {
        "full_name": "Beijing",
        "tag_name": "cn1",
    },
    "ap-southeast-1": {
        "full_name": "Singapore",
        "tag_name": "aps1",
    },
    "eu-west-1": {
        "full_name": "Ireland",
        "tag_name": "eu",
    },
    "us-east-1": {
        "full_name": "N. Virginia",
        "tag_name": "use1",
    },
}

AWS_CREDENTIALS = {
    "cn-alpha": {
        "regions": [
            "cn-north-1",
        ],
    },
    "cn-beta": {
        "regions": [
            "cn-north-1",
        ],
    },
    "cn-prd": {
        "regions": [
            "cn-north-1",
        ],
    },
    "global-alpha": {
        "regions": [
            "ap-southeast-1",
            "eu-west-1",
            "us-east-1",
        ],
    },
    "global-beta": {
        "regions": [
            "ap-southeast-1",
            "eu-west-1",
            "us-east-1",
        ],
    },
    "global-prd": {
        "regions": [
            "ap-southeast-1",
            "eu-west-1",
            "us-east-1",
        ],
    },
}

MODULES = {
    "cn-prd": {
        "cn-north-1": [
            {
                "name": "connector",
                "previous_version": "0",
                "current_version": "2.0.1",
                "instance_count": 50,
                "configuration": "",
                "load_balancer_names": "prd-elb-connector-cn1-0",
            },
            {
                "name": "connector",
                "previous_version": "2.0.1",
                "current_version": "2.0.4",
                "instance_count": 50,
                "configuration": "",
                "load_balancer_names": "prd-elb-connector-cn1-0",
            },
            {
                "name": "dispatcher",
                "previous_version": "0",
                "current_version": "1.1.11",
                "instance_count": 10,
                "configuration": "",
                "load_balancer_names": "",
            },
            {
                "name": "dispatcher",
                "previous_version": "1.1.11",
                "current_version": "2.0.3",
                "instance_count": 10,
                "configuration": "",
                "load_balancer_names": "",
            },
        ]
    }
}



def cmp_version(ver1, ver2):
    """Compare version numbers."""
    arr_ver1 = ver1.split('.')
    arr_ver2 = ver2.split('.')
    len1 = len(arr_ver1)
    len2 = len(arr_ver2)
    # number of comparisons to make:
    cmp_count = min(len1, len2)
    i = 0
    # compare each segment:
    while i < cmp_count:
        try:
            m = int(arr_ver1[i])
        except:
            raise Exception(
                "Cannot parse segment as integer: %s."%(arr_ver1[i])
            )
        try:
            n = int(arr_ver2[i])
        except:
            raise Exception(
                "Cannot parse segment as integer: %s."%(arr_ver2[i])
            )
        if m < n:
            return -1
        if m > n:
            return 1
        i += 1
    # if segments are the same, the longer one wins:
    if len1 < len2:
        return -1
    if len1 > len2:
        return 1
    # otherwise return equal:
    return 0


def install_regions():
    """Add default regions to database."""
    print("Adding default regions ...")
    for region_name in sorted(AWS_REGIONS.keys()):
        try:
            AWSRegion.objects.get(name=region_name)
            print("Region %s already installed ..."%(region_name,))
        except:
            print("Installing region %s ..."%(region_name,))
            region = AWSRegion(
                name=region_name,
                full_name=AWS_REGIONS[region_name]['full_name'],
                tag_name=AWS_REGIONS[region_name]['tag_name'],
                )
            region.save()
    print("Regions installed.\n")


def install_profiles():
    """Add default profiles and associate regions."""
    print("Adding default profiles ...")
    for profile_name in sorted(AWS_CREDENTIALS.keys()):
        try:
            profile = AWSProfile.objects.get(name=profile_name)
            print("Profile %s already installed."%(
                profile_name,
            ))
        except:
            print("Adding profile %s ..."%(profile_name,))
            profile = AWSProfile(
                name=profile_name,
                aws_access_key_id="",
                aws_secret_access_key="")
            profile.save()
        print("Checking regions ...")
        region_names = AWS_CREDENTIALS[profile_name]['regions']
        for region_name in sorted(region_names):
            try:
                region = AWSRegion.objects.get(name=region_name)
            except:
                print("WARING: Region %s not found. Skipping ..."%(region_name,))
                continue
            if region not in profile.regions.all():
                print("Adding region %s to profile %s ..."%(
                    region_name,
                    profile_name,
                ))
                profile.regions.add(region)
            profile.save()
    print("Profiles installed.\n")


def install_sample_modules():
    print("Adding sample modules ...")
    for profile_name in sorted(MODULES.keys()):
        print("Creating modules for profile %s ..."%(profile_name,))
        profile = AWSProfile.objects.get(name=profile_name)
        for region_name in sorted(MODULES[profile_name].keys()):
            region = AWSRegion.objects.get(name=region_name)
            print("Creating modules in region %s ..."%(region_name,))
            for module_info in MODULES[profile_name][region_name]:
                try:
                    module = Module.objects.get(
                        name=module_info['name'],
                        current_version = module_info['current_version']
                    )
                    print("Module %s-%s already installed."%(
                        module_info['name'],
                        module_info['current_version']
                    ))
                except:
                    print("Creating module %s-%s ..."%(
                        module_info['name'],
                        module_info['current_version']
                    ))
                    module = Module(
                        name=module_info['name'],
                        profile=profile,
                        region=region,
                        current_version=module_info['current_version'],
                        previous_version=module_info['previous_version'],
                        instance_count=module_info['instance_count'],
                        configuration=module_info['configuration'],
                        load_balancer_names=module_info['load_balancer_names']
                    )
                    module.save()
    print("Modules installed.\n")


def install_sample_updateplan():
    plan = UpdatePlan(
        project_name="Simple Plan",
        project_code="simpleplan",
        project_leader="Chuck Norris",
        note="A sample UpdatePlan"
    )
    plan.save()
    step1 = UpdateStep(
        sequence=2,
        module=Module.objects.get(pk=7),
        start_time=datetime.datetime.strptime("20170104180000","%Y%m%d%H%M%S")
    )
    step1.save()
    step2 = UpdateStep(
        sequence=1,
        module=Module.objects.get(pk=16),
        start_time=datetime.datetime.strptime("20170104170000","%Y%m%d%H%M%S")
    )
    step2.save()
    plan.steps.add(step1)
    plan.steps.add(step2)
    

def main():
    install_regions()
    install_profiles()
    install_sample_modules()
    install_sample_updateplan()

if __name__ == "__main__":
    main()
