"""
Hello!
"""

import json
import os
import pytz
import datetime

from fabric.api import *
from ec2mgr.models import EC2Instance

# define timezone:
TZ = "Asia/Chongqing"
# new instances should enter service within (seconds):
READY_THRESHOLD = 300

class CheckTaskException(Exception):
    pass


class EC2CheckTask:
    """Check EC2 service status via fabric/ssh"""
    def __init__(self, module, ec2instance, pem_dir):
        self.module = module
        self.ec2instance = ec2instance
        self.pem_dir = pem_dir
        self.host_string = "%s@%s"%(
            ec2instance.username, 
            ec2instance.private_ip_address
        )
        self.key_filename = os.path.sep.join([
            pem_dir,
            self.ec2instance.key_pair + ".pem"
        ])
        self.service_status = self.ec2instance.service_status
        if self.ec2instance.service_status == "not_ready"
            self.is_new_instance = True
        else:
            self.is_new_instance = False

        self.timezone = pytz.timezone(TZ)


    def set_fabric_env(self):
        global env
        env.hosts = [self.host_string]
        env.host_string = self.host_string
        env.key_filename = self.key_filename


    def check_process(self, process_name):
        """check if <process_name> is running."""
        cmd = "ps -ef|grep '%s'|grep -v grep|wc -l"%(process_name,)
        r = run(cmd)
        if r.return_code != 0:
            raise Exception("Command didn't return 0!")
        return int(r) > 0

    
    def check_file_content(self, substr, filepath):
        """check if <filepath> contains <substr>."""
        cmd = "grep '%s' %s|wc -l"%(substr, filepath)
        r = run(cmd)
        if r.return_code != 0:
            raise Exception("Command didn't return 0!")
        return int(r) > 0


    def check_java_service(self):
        """check if java service process is running."""
        process_name = self.module.name + \
            "-" + \
            self.module.version
        return self.check_process(process_name)


    def check_tomcat_service(self):
        statuspath = "/home/ubuntu/cloud-%s/cloud-%s-%s/WEB-INF/classes"%(
            self.module.name, 
            self.module.name, 
            self.module.version
        )
        statuspath = statuspath + "/status.sh"
        r = run("/bin/bash "+statuspath)
        return r.find("is running") != -1


    def check_generic_service(self):
        return self.check_process(self.module.name)


    def check_nohup_output(self):
        substr = "cloud-%s service started"%(self.module.name,)
        filepath = os.path.sep.join([
            "~",
            "cloud-"+self.module.name,
            "cloud-"+self.module.name+"-"+self.module.version,
            "logs",
            "nohup.out"
        ])
        return self.check_file_content(substr, filepath)


    def check_log_script(self):
        cmd = "ps -ef|grep 'logpackage'|grep -v grep|wc -l"
        r = run(cmd)
        if int(r) == 0:
            return False
        cmd = "ps -ef|grep 'logtransfer'|grep -v grep|wc -l"
        r = run(cmd)
        return int(r) > 0


    def check_falcon_agent(self):
        cmd = "ps -ef|grep 'falcon-agent'|grep -v grep|wc -l"
        r = run(cmd)
        return int(r) > 0


    def perform_check(self, check_name):
        check_func = getattr(self, "check_"+check_name)
        with settings(abort_exception=CheckTaskException):
            try:
                r = check_func()
                if not r:
                    self.ec2instance.service_status = "down"
                    self.ec2instance.note += "%s check failed.\r\n"%(check_name,)
            except:
                self.ec2instance.service_status = "down"
                self.ec2instance.note += "Cannot perform %s check.\r\n"%(check_name,)
            return (self.ec2instance.service_status, self.ec2instance.note)


    def check_instance(self):
        self.set_fabric_env()
        # set default value:
        self.ec2instance.service_status = "ok"
        self.ec2instance.note = ""
        # get svc type and perform different checks accordingly:
        if self.module.service_type == "java":
            # module is a java service:
            ## check java process:
            self.perform_check("java_service")
            ## check nohup output for "xxx service started":
            self.perform_check("nohup_output")
        elif self.module.service_type == "tomcat":
            # module is a tomcat service:
            ## check tomcat process:
            self.perform_check("tomcat_service")
        else:
            # when not sure what service it is:
            ## check process with module name:
            self.perform_check("generic_service")
        # checks for all modules:
        ## check log script:
        self.perform_check("log_script")
        ## check open-falcon agent:
        self.perform_check("falcon_agent")
        # record time:
        now = self.timezone.localize(datetime.datetime.now())
        # if host is a new ec2instance and service down:
        if self.is_new_instance:
            dt = now - self.ec2instance.created_at
            if dt.seconds < READY_THRESHOLD:
                if not self.ec2instance.service_ok:
                    self.ec2instance.set_not_ready()
        # save results:
        self.ec2instance.save()
        print("STATUS: "+self.ec2instance.service_status)
        print("NOTE: \r\n"+self.ec2instance.note)
        print("\r\n")

