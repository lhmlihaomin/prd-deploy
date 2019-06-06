#!/usr/bin/python
"""
Standalone program to stop given EC2 instances.
Will be called when user asks to stop instances from webpage.
Runs in the background and updates instance statuses in database.
User will need to refresh the webpage to see the latest instance status.
Usage: python stop_ec2_instances.py <instance_id_1> <instance_id_2> ...
"""

import sys
import os
import django
import threading
import time

# Initialize django environment:
sys.path.append(os.path.abspath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'PrdDeployer.settings'
django.setup()

from ec2mgr.models import EC2Instance
from schtasks.ssh import SshHandler

class StopInstanceWorker(threading.Thread):
    def __init__(self, ec2_instance, key_path):
        """Read module info and init SSH connection."""
        threading.Thread.__init__(self)
        self.instance = ec2_instance
        self.key_path = key_path
        self.ssh = None

    def connect_ssh(self):
        if self.ssh is None:
            self.ssh = SshHandler(self.instance, self.key_path)

    def disconnect_ssh(self):
        if self.ssh is not None:
            self.ssh.close()

    def stop_service(self):
        """Stop service process."""
        # assemble stop command:
        cmd = self.instance.stop_command
        print(cmd)
        try:
            exit_code, output, err = self.ssh.run(cmd)
            print(exit_code)
            if exit_code != 0:
                return False
        except:
            return False
        return True

    def upload_final_logs(self):
        """Package remaining logs and initiate upload."""
        log_script_path = "~"
        log_script = "logpackage.py"
        new_log_script_path = "~/cloud-ops/log_transfer"
        new_log_script = "log_service_shutdown.sh"
        # run command and wait for it to finish:
        #self.ssh.run(self.instance.stop_command)
        cmd = "cd %s&&python %s true"%(log_script_path, log_script)
        new_cmd = "cd %s&&bash %s"%(new_log_script_path, new_log_script)
        print(cmd)
        try:
            exit_code, output, err = self.ssh.run(cmd)
            print(exit_code)
        except:
            return False
        if exit_code != 0:
            try:
                exit_code, output, err = self.ssh.run(new_cmd)
                print(exit_code)
                if exit_code != 0:
                    return False
            except:
                return False
        # sleep (a magical) 10 seconds:
        #time.sleep(10)
        return True

    def shutdown_instance(self):
        """Shut down the instance."""
        # run shutdown command with a delay, so that we have time to
        # disconnect from the machine:
        cmd = "sudo shutdown -P +1 &"
        print(cmd)
        try:
            exit_code, output, err = self.ssh.run(cmd)
            print(exit_code)
            if exit_code != 0:
                return False
        except:
            return False
        return True


    def run(self):
        self.connect_ssh()
        print("stopping service ...")
        # mark instance as retired:
        self.instance.retired = True
        result = self.stop_service()
        if not result:
            # write error
            self.instance.service_status = "error"
            self.instance.note = "Failed to stop service."
            self.instance.save()
            return False
        else:
            self.instance.service_status = "stopped"
            self.instance.save()
        print("uploading logs ...")
        result = self.upload_final_logs()
        if not result:
            # write error
            self.instance.service_status = "error"
            self.instance.note = "Failed to upload log."
            self.instance.save()
            return False
        print("shutting down ...")
        result = self.shutdown_instance()
        print(result)
        if not result:
            # write error:
            self.instance.running_state = "error"
            self.instance.note = "Failed to shutdown instance."
            self.instance.save()
            return False
        else:
            self.instance.running_state = "stopping"
            self.instance.retired = True    # mark instance as retired
            self.instance.save()
        return True


def main():
    try:
        # parse arguments:
        ec2_instance_ids = sys.argv[1:]
        if len(ec2_instance_ids) == 0:
            print("Usage: python stop_ec2_instances.py <instance_id_1> <instance_id_2> ...")
            sys.exit(1)
    except Exception as ex:
        print("Usage: python stop_ec2_instances.py <instance_id_1> <instance_id_2> ...")
        sys.exit(1)
    # read instance and module information:
    ec2_instances = EC2Instance.objects.filter(pk__in=ec2_instance_ids)
    #ec2_instances = EC2Instance.objects.all()
    # start workers:
    workers = list()
    for ec2_instance in ec2_instances:
        print("===== %s ====="%(ec2_instance.name))
        worker = StopInstanceWorker(ec2_instance, '/home/ubuntu/pem/')
        workers.append(worker)
        worker.start()
        print("-------------------------------------")
    # wait for workers to join:
    for worker in workers:
        worker.join()


if __name__ == "__main__":
    main()
