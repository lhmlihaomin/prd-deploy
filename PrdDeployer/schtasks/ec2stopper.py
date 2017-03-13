"""
A class that handles EC2Instances that have been marked as 'to_stop'.
Step 1. The module and service_type of this instance is read to determine how 
        its application and services should be stopped. 
Step 2. The corresponding stop_* methods are invoked to send SSH commands to 
        this instance.
Step 3. If the stop commands return no error, the instance's service_status 
        will be marked as 'stopped'. The timestamp is also recorded. The 
        instance itself will not be stopped immediately since there might be 
        unfinished background tasks, such as uploading final log files.
Step 4. If an instance has been marked as serivce stopped for longer than 
        'STOP_THRESHOLD' seconds (set in settings.py), boto3's stop_instances 
        method is called to stop it for real.

if service_status == 'to_stop':
    check service_type
    result = stop_*()
    if no error:
        instance.service_status = 'stopped'
    else:
        instance.service_status = 'error'
        instance.note = error
    instance.service_stopped_at = now

if service_status == 'stopped':
    if now - instance.service_stopped_at > STOP_THRESHOLD:
        boto3.stop(instance)
        instance.running_state = new_state
        instance.service_status = 'down'
    else:
        do nothing
"""

import time
import os
import sys
import pytz
import django
import datetime
import threading

from schtasks.ssh import SshHandler

class EC2CheckerException(Exception):
    pass


class EC2Stopper(object):
    def __init__(self, module, ec2instance, pem_dir, service_types, tzname, stop_timeout):
        self.module = module
        self.ec2instance = ec2instance 
        self.pem_dir = pem_dir
        self.service_types = service_types
        self.key_filename = os.path.sep.join([
            pem_dir,
            self.ec2instance.key_pair + ".pem"
        ])
        
        self.timezone = pytz.timezone(tzname)
        self.stop_timeout = stop_timeout

        self.generic_actions = (
            'stop_logpackage',
        )

        self.service_actions = {
            'java': (
                'stop_java_service',
            ),
            'tomcat': (
                'stop_tomcat',
            ),
            'echo_server': (
                'stop_echo_server',
            ),
            'tomcat_aptget': (
                'stop_tomcat_aptget',
            )
        }

    def cmd_stop_java_service(self, name, version):
        stoppath = "/home/ubuntu/cloud-%s/cloud-%s-%s/bin"%(
            name,
            name,
            version
        )
        stoppath = stoppath + "/stop.sh"
        cmd = "/bin/bash " + stoppath + ";echo $?|tail -n1"
        return cmd

    def cmd_stop_tomcat(self, name, version):
        stoppath = "/home/%s/cloud-%s/cloud-%s-%s/WEB-INF/classes"%(
            self.ec2instance.username,
            name,
            name,
            version
        )
        stoppath = stoppath + "/stop.sh"
        cmd = "/bin/bash " + stoppath + ";echo $?|tail -n1"
        return cmd

    def cmd_stop_logpackage(self):
        logpackagepath = "/home/%s/logpackage.py"%(self.ec2instance.username,)
        cmd = "/usr/bin/python " + logpackagepath + " true"
        return cmd

    def cmd_stop_echo_server(self, module, version):
        cmd = "stop echo server"
        return cmd

    def cmd_stop_tomcat_aptget(self, module, version):
        cmd = "stop tomcat aptget"
        return cmd

    def assemble_generic_cmd(self):
        actions = []
        cmds = []
        for action_name in self.generic_actions:
            action_func = getattr(self, 'cmd_'+action_name)
            actions.append(action_name)
            cmds.append(action_func())
        return (actions, cmds)

    def assemble_module_cmd(self, module_name, version):
        actions = []
        cmds = []
        if self.service_types.has_key(module_name):
            service_type = self.service_types[module_name]
            if self.service_actions.has_key(service_type):
                for action_name in self.service_actions[service_type]:
                    action_func = getattr(self, 'cmd_'+action_name)
                    actions.append(action_name)
                    cmds.append(action_func(module_name, version))
        return (actions, cmds)

    def assemble_stop_cmd(self):
        actions = []
        cmds = []
        # Stop each module deployed:
        module_names = self.module.name.split('_')
        versions = self.module.current_version.split('_')
        service_types = self.module.service_type.split('_')
        mod_count = len(module_names)
        print(module_names)
        print(versions)
        for i in range(mod_count):
            module_name = module_names[i]
            version = versions[i]
            if self.service_types.has_key(module_name):
                service_type = self.service_types[module_name]
                print(service_type)
            else:
                #continue
                # skip instances with unknown services:
                return ([], [])
            mod_actions, mod_cmds = self.assemble_module_cmd(module_name, version)
            actions += mod_actions
            cmds += mod_cmds
        # stop background scripts after modules have been stopped
        generic_actions, generic_cmds = self.assemble_generic_cmd()
        actions += generic_actions
        cmds += generic_cmds
        return (actions, cmds)

    def run_stop_commands(self):
        # only stop services on hosts marked as 'to_stop'
        if self.ec2instance.service_status == "to_stop":
            # check service type and assemble commands to run:
            results = {}
            actions, cmds = self.assemble_stop_cmd()
            self.ssh = SshHandler(self.ec2instance, self.pem_dir)
            for i in range(len(actions)):
                try:
                    exit_code, output, err = self.ssh.run(cmds[i])
                    results.update({
                        actions[i]: exit_code == 0
                    })
                except Exception as ex:
                    print(ex)
                    results.update({
                        actions[i]: False
                    })
            self.ec2instance.service_status = "stopped"
            now = self.timezone.localize(datetime.datetime.now())
            self.ec2instance.service_stopped_at = now
            return results
        # if service already stopped, shutdown those stopped longer than 
        # STOP_TIMEOUT
        if self.ec2instance.service_status == "stopped":
            now = self.timezone.localize(datetime.datetime.now())
            dt = now - self.ec2instance.service_stopped_at
            # do nothing if instance service hasn't been stopped for 
            # STOP_TIMEOUT seconds:
            if dt.seconds < self.stop_timeout:
                return
            # stop the instance and update running_state:
            s = self.module.profile.get_session(self.module.region)
            e = s.resource('ec2')
            instance = e.Instance(self.ec2instance.instance_id)
            resp = instance.stop()
            #self.ec2instance.running_state = \
            #    resp['StoppingInstances'][0]['CurrentState']['Name']
            self.ec2instance.running_state = instance.state['Name']
            self.ec2instance.last_checked_at = \
                self.timezone.localize(datetime.datetime.now())
            return


class StopperRunner(threading.Thread):
    def __init__(self, ec2stopper):
        threading.Thread.__init__(self)
        self.ec2stopper = ec2stopper

    def run(self):
        results = self.ec2stopper.run_stop_commands()
        return True
        