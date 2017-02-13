"""
A class to check EC2 instances with differennt types of service.
TODO:
1. update instance running states before doing anything else.
   (will require calling boto3 methods)
2. add new instance specific checks:
    a. ntp server configuration;
    b. unexpected crontab shutdown;
3. less intense ssh checks for healthy instances (?)
4. rewrite using paramiko
"""

import json
import os
import sys
import pytz
import datetime
import django
import threading

# Initialize django environment:
sys.path.append(os.path.abspath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'PrdDeployer.settings'
django.setup()

from fabric.api import *
from ec2mgr.models import EC2Instance
from awscredentialmgr.models import AWSProfile, AWSRegion
from updateplanmgr.models import Module
from awsresourcemgr.models import NTPServerDefinition

from django.conf import settings as djconf


class EC2CheckerException(Exception):
    pass


class EC2Checker(object):
    def __init__(self, module, ec2instance, pem_dir, service_types, tzname, ready_threshold):
        self.module = module
        self.ec2instance = ec2instance
        self.pem_dir = pem_dir
        self.service_types = service_types
        self.host_string = "%s@%s"%(
            ec2instance.username,
            ec2instance.private_ip_address
        )
        self.key_filename = os.path.sep.join([
            pem_dir,
            self.ec2instance.key_pair + ".pem"
        ])
        self.service_status = self.ec2instance.service_status
        if self.ec2instance.service_status == "not_ready":
            self.is_newinstance = True
        else:
            self.is_newinstance = False

        self.timezone = pytz.timezone(tzname)
        self.ready_threshold = ready_threshold

        self.service_checks = {
            'java': (
                'java_service',
                'nohup_output',
            ),
            'tomcat':(
                'tomcat_service',
            ),
            'echo_server': (
                'echo_server',
            ),
            'tomcat_aptget': (
                'tomcat',
            )
        }
        self.generic_checks = (
            'logpackage',
            'logtransfer',
            'falcon_agent',
        )
        self.newinstance_checks = (
            'ntp_server',
            'crontab_shutdown',
        )

    def set_fabric_env(self):
        """initialize fabric 'env' variable for execution"""
        global env
        env.host_string = self.host_string
        env.key_filename = self.key_filename

    def cmd_process(self, process_name):
        cmd = "ps -ef|grep '%s'|grep -v grep|wc -l"%(process_name,)
        return cmd

    def cmd_file_content(self, substr, filepath):
        """command to search 'filepath' for 'substr'"""
        cmd = "grep '%s' %s|wc -l"%(substr, filepath)
        return cmd

    def cmd_java_service(self, name, version):
        process_name = name + \
            "-" + \
            version
        return self.cmd_process(process_name)

    def cmd_tomcat_service(self, name, version):
        statuspath = "/home/ubuntu/cloud-%s/cloud-%s-%s/WEB-INF/classes"%(
            name,
            name,
            version
        )
        statuspath = statuspath + "/status.sh"
        cmd = "/bin/bash " + statuspath + "|grep 'is running'|wc -l"
        return cmd

    def cmd_echo_server(self, name, version):
        process_name = 'EchoServer'
        return self.cmd_process(process_name)

    def cmd_tomcat(self, name, version):
        process_name = 'tomcat'
        return self.cmd_process(process_name)

    def cmd_nohup_output(self, name, version):
        if name == "connector":
            substr = "service start success"
        else:
            substr = "cloud-%s service started"%(name,)
        filepath = os.path.sep.join([
            "~",
            "cloud-"+name,
            "cloud-"+name+"-"+version,
            "logs",
            "nohup.out"
        ])
        return self.cmd_file_content(substr, filepath)

    def cmd_logpackage(self):
        cmd = "ps -ef|grep 'logpackage'|grep -v grep|wc -l"
        return cmd

    def cmd_logtransfer(self):
        cmd = "ps -ef|grep 'logtransfer'|grep -v grep|wc -l"
        return cmd

    def cmd_falcon_agent(self):
        cmd = "ps -ef|grep 'falcon-agent'|grep -v grep|wc -l"
        return cmd

    def cmd_ntp_server(self):
        ntpd = NTPServerDefinition.objects.get(vpc_id=self.ec2instance.vpc_id)
        cmd = "grep -e '^server %s' /etc/ntp.conf|wc -l"%(ntpd.address,)
        return cmd

    def cmd_crontab_shutdown(self):
        #cmd = 'echo "$((`crontab -l|grep shutdown|wc -l`+1))"'
        cmd = 'echo 1'
        return cmd


    def assemble_generic_cmd(self):
        checks = []
        cmds = []
        for check_name in self.generic_checks:
            print("getting cmd "+check_name)
            check_func = getattr(self, 'cmd_'+check_name)
            checks.append(check_name)
            cmds.append(check_func())
        return (checks, cmds)

    def assemble_module_cmd(self, module_name, version):
        checks = []
        cmds = []
        if self.service_types.has_key(module_name):
            service_type = self.service_types[module_name]
            if self.service_checks.has_key(service_type):
                for check_name in self.service_checks[service_type]:
                    check_func = getattr(self, 'cmd_'+check_name)
                    checks.append(check_name)
                    cmds.append(check_func(module_name, version))
        return (checks, cmds)

    def assemble_newinstance_cmd(self):
        checks = []
        cmds = []
        for check_name in self.newinstance_checks:
            check_func = getattr(self, 'cmd_'+check_name)
            checks.append(check_name)
            cmds.append(check_func())
        return (checks, cmds)

    def assemble_check_cmd(self):
        checks = []
        cmds = []
        if self.is_newinstance:
            newinstance_checks, newinstance_cmds = self.assemble_newinstance_cmd()
            checks += newinstance_cmds
            cmds += newinstance_cmds
        generic_checks, generic_cmds = self.assemble_generic_cmd()
        checks += generic_checks
        cmds += generic_cmds
        # EC2 instance may have multiple modules installed:
        module_names = self.module.name.split('_')
        versions = self.module.current_version.split('_')
        service_types = self.module.service_type.split('_')
        mod_count = len(module_names)
        for i in range(mod_count):
            module_name = module_names[i]
            version = versions[i]
            if self.service_types.has_key(module_name):
                service_type = self.service_types[module_name]
            else:
                #continue
                # skip instances with unknown services:
                return ([], [])
            mod_checks, mod_cmds = self.assemble_module_cmd(module_name, version)
            checks += mod_checks
            cmds += mod_cmds
        return (checks, cmds)

    def perform_check(self):
        # update instance information if it's in an "unstable" state:
        if self.ec2instance.running_state in ('pending', 'stopping', 'shutting-down'):
            try:
                s = self.module.profile.get_session(self.module.region)
                e = s.resource('ec2')
                instance = e.Instance(self.ec2instance.instance_id)
                self.ec2instance.running_state = instance.state['Name']
                self.ec2instance.save()
            except:
                print("!!! Cannot describe instance. Instance might have been terminated.")
                self.ec2instance.running_state = "Terminated"
                self.ec2instance.save()
                return {}
        results = {}
        checks, cmds = self.assemble_check_cmd()
        if len(checks) == 0:
            return results
        cmd = ";".join(cmds)
        print(cmd)
        self.set_fabric_env()
        with settings(abort_exception=EC2CheckerException), hide('running', 'stdout', 'stderr'):
            try:
                r = run(cmd)
                outputs = r.stdout.replace("\r", "").split("\n")
                for i, output in enumerate(outputs):
                    results.update({
                        checks[i]: int(output) == 1
                    })
            except Exception as ex:
                print("!!! "+ex.message)
                for check_name in checks:
                    results.update({
                        check_name: False
                    })
                try:
                    print("!!! Checking if this instance is terminated.")
                    s = self.module.profile.get_session(self.module.region)
                    e = s.resource('ec2')
                    instance = e.Instance(self.ec2instance.instance_id)
                    instance.load()
                    print(instance.vpc_id)
                    print(instance.key_pair)
                    self.ec2instance.running_state = instance.state['Name']
                    print("!!! "+instance.id)
                except:
                    print("!!! Cannot describe instance. Instance might have been terminated.")
                    self.ec2instance.running_state = "Terminated"
                    self.ec2instance.save()
                    return {}
                return results
        return results

    def save_results(self, results):
        if len(results.keys()) == 0:
            self.ec2instance.service_status = "N/A"
            self.ec2instance.note = "Unknown service. No checks run."
            self.ec2instance.save()
            return
        self.ec2instance.service_status = "ok"
        self.ec2instance.note = ""
        # update last check time:
        now = self.timezone.localize(datetime.datetime.now())
        self.ec2instance.last_checked_at = now
        for check_name in results.keys():
            if not results[check_name]:
                # some check failed:
                if self.is_newinstance:
                    # if it's just started, mark as not_ready:
                    dt = now - self.ec2instance.created_at
                    if dt.seconds < self.ready_threshold:
                        self.ec2instance.set_not_ready()
                        break
                # otherwise mark as down:
                self.ec2instance.service_status = "down"
                self.ec2instance.note += "%s check failed.\n"%(check_name,)
        self.ec2instance.save()


class CheckRunner(threading.Thread):
    def __init__(self, ec2checker):
        threading.Thread.__init__(self)
        self.ec2checker = ec2checker

    def run(self):
        results = self.ec2checker.perform_check()
        self.ec2checker.save_results(results)
        return True

