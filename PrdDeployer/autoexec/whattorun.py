import os
import sys
import datetime
import time
import subprocess

import pytz
import django
import boto3

# Django setup:
# Django setup:
sys.path.append(
    os.path.abspath(
       os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir)
    )
)
os.environ['DJANGO_SETTINGS_MODULE'] = 'PrdDeployer.settings'
django.setup()

from django.contrib.auth.models import User
from django.conf import settings

from updateplanmgr.models import UpdatePlan, UpdateStep, Module, UpdateActionLog
from ec2mgr.models import EC2Instance
from ec2mgr.ec2 import run_instances, add_instance_tags_ex, add_volume_tags_ex

PIDFILE = "/tmp/autoexec.pid"
PIDCMD = "ps -f `cat {0}`|grep 'autoexec'|wc -l".format(PIDFILE)

tz = pytz.timezone("Asia/Shanghai")
plan = UpdatePlan.objects.filter(finished=False)\
                         .filter(start_time__lt=datetime.datetime.now(tz))\
                         .filter(error=False)\
                         .first()

if plan is None:
    exit()


'''
# user confirm:
i = raw_input("Continue? ")
if i != 'Y':
    exit()
'''


# check if autoexec is already running:
if os.path.isfile(PIDFILE):
    p = subprocess.Popen([PIDCMD,], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if len(stderr) > 0:
        print("Failed to check autoexec process. Command line: "+PIDCMD)
        sys.exit()
    if int(stdout) != 1:
        print("Failed to check autoexec process. Please make sure autoexec terminated normally.")
        sys.exit()
    print("Autoexec is already running.")
    sys.exit()
pass

# start autoexec:
autoexec_path = os.path.sep.join([
    os.path.dirname(os.path.abspath(__file__)),
    "autoexec.py"
])
#print(" ".join(['python', autoexec_path, str(plan.id)]))
p = subprocess.Popen(['python', autoexec_path, str(plan.id)])

