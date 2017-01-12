"""
Script to import JSON files from old "Ec2Launcher".
"""

import re
import os
import sys
import django

# Initialize django environment:
sys.path.append(os.path.abspath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'PrdDeployer.settings'
django.setup()

from awscredentialmgr.models import AWSRegion, AWSProfile
from updateplanmgr.models import Module

JSONDIR = os.path.sep.join([os.path.expanduser('~'), 'json'])



def main():
    for fname in os.listdir(JSONDIR):
        fpath = os.path.sep.join([JSONDIR, fname])
        (profile_name, 
        region_name, 
        module_name, 
        version_name) = fname[:-5].split('#')
        with open(fpath, 'r') as fp:
            content = fp.read()
            profile = AWSProfile.objects.get(name=profile_name)
            region = AWSRegion.objects.get(name=region_name)
            try:
                module = Module.objects.get(
                    profile=profile,
                    region=region,
                    name=module_name,
                    current_version=version_name
                )
                print("Module (%s, %s) %s-%s already there."%(profile_name,
                    region_name, module_name, version_name))
            except:
                print("Creating module (%s, %s) %s-%s ..."%(profile_name,
                    region_name, module_name, version_name))
                module = Module(
                    name=module_name,
                    profile=profile,
                    region=region,
                    current_version=version_name,
                    previous_version="0",
                    is_online_version=True,
                    instance_count=0,
                    configuration=content,
                    load_balancer_names=""
                )
                module.save()

if __name__ == "__main__":
    main()
