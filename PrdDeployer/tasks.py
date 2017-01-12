"""
Background recurring tasks.
"""

import os
import sys
import django
import datetime
import json

KEY_FILEPATH = "/home/ubuntu/PrdDeployer/pem/"

# Initialize django environment:
sys.path.append(os.path.abspath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'PrdDeployer.settings'
django.setup()


from fabric.api import *
from updateplanmgr.models import Module
from ec2mgr.models import EC2Instance

@task
def check_process(proc):
    cmd = "ps -ef|grep '%s'|grep -v grep|wc -l"%(proc,)
    run(cmd)


@task
def check_tomcat_service(name, version):
    statuspath = "/home/ubuntu/cloud-%s/cloud-%s-%s/WEB-INF/classes"%(name, name, version)
    statuspath = statuspath + "/status.sh"
    run("/bin/bash "+statuspath)


@task
def check_java_service(name, version):
    cmd = "ps -ef|grep '%s-%s'|grep -v grep|wc -l"%(name, version)
    run(cmd)


@task
def check_nohup_output(name, version):
    outpath = "/home/ubuntu/cloud-%s/cloud-%s-%s/logs/nohup.out"%(name, name, version)
    cmd = "tail -n1 "+outpath
    run(cmd)


@task
def check_log_script():
    cmd = "ps -ef|grep 'logpackage'|grep -v grep|wc -l"
    run(cmd)
    cmd = "ps -ef|grep 'logtransfer'|grep -v grep|wc -l"
    run(cmd)

@task
def check_falcon_agent():
    cmd = "ps -ef|grep 'falcon-agent'|grep -v grep|wc -l"
    run(cmd)


@task
def check_new_instance(name, version):
    if name in ['appserver', 'appserverinternal', 'storage']:
        proc = name
        check_tomcat_service(name, version)
    elif name == 'dns':
        proc = 'named'
        check_process(proc)
    else:
        check_java_service(name, version)
        check_nohup_output(name, version)

    check_log_script()
    check_falcon_agent()


@task
def check_apache2():
    cmd = "ps -ef|grep apache2|grep -v grep|wc -l"
    r = run(cmd)
    if r.return_code != 0:
         raise Exception("Command didn't return 0.")
    return int(r) > 0

@task
def check_file_content(substr, filepath):
    cmd = "grep '%s' %s|wc -l"%(substr, filepath)
    r = run(cmd)
    if r.return_code != 0:
        raise Exception("Command didn't return 0.")
    return int(r) > 0

def check_service_status():
    return check_file_content(
        'apache2 service started',
        '/home/ubuntu/nohup.out'
    )

def main():
    results = {}
    checks = {
        'apache2': check_apache2,
        'Service Status': check_service_status
    }

    module = Module.objects.get(name='mod1', current_version='1.2.1')
    for ec2instance in module.instances.all():
        print ec2instance.instance_id
        env.host_string = "%s@%s"%(ec2instance.username, ec2instance.private_ip_address)
        env.key_filename = KEY_FILEPATH + ec2instance.key_pair + ".pem"
        host_result = {}
        for check_name in checks:
            check_func = checks[check_name]
            host_result.update({check_name: check_func()})
        results.update({ec2instance.name: host_result})

    print(json.dumps(results, indent=2))
        

if __name__ == "__main__":
    main()

