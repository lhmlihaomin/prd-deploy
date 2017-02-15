#!/usr/bin/python

import os
import sys

import django
import paramiko

# Initialize django environment:
sys.path.append(os.path.abspath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'PrdDeployer.settings'
django.setup()

from django.conf import settings
from ec2mgr.models import EC2Instance
from schtasks.ssh import SshHandler


ec2instance = EC0Instance.objects.get(pk=1)

with SshHandler(ec2instance, settings.PEM_DIR) as sh:
    code, output = sh.run('ls -lh /')
    print("OUTPUT: "+output)
    print("\n==================\nEXIT CODE: "+str(code))

