"""
Hello!
"""

import json
import os

from fabric.api import *
from ec2mgr.models import EC2Instance

class EC2CheckTask:
    """Check EC2 service status via fabric/ssh"""
    def __init__(self, ec2instance, pem_dir):
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


    def set_fabric_env(self):
        global env
        env.hosts = [self.host_string]
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


    def check_java_service(module_name, module_version):
        """check if java service process is running."""
        process_name = module_name + "-" + module_version
        return self.check_process(process_name)


    def check_nohup_output(module_name, module_version):
        substr = "cloud-%s service started"%(module_name,)
        filepath = os.path.sep.join([
            "~",
            "cloud-"+module_name,
            "cloud-"+module_name+"-"+module_version,
            "logs",
            "nohup.out"
        ])
        return self.check_file_content(substr, filepath)

