#!/usr/bin/python
"""
Standalone program to stop given EC2 instances.
Will be called when user asks to stop instances from webpage.
Runs in the background and updates instance statuses in database.
User will need to refresh the webpage to see the latest instance status.
Usage: python stop_ec2_instances.py <instance_id_1> <instance_id_2> ...
"""

import django

# Initialize django environment:
sys.path.append(os.path.abspath(__file__))
os.environ['DJANGO_SETTINGS_MODULE'] = 'PrdDeployer.settings'
django.setup()

import threading

class StopInstanceWorker(threading.Thread):
    def __init__(self):
        """Read module info and init SSH connection."""
        threading.Thread.__init__(self)
        pass

    def stop_service(self):
        """Stop service process."""
        # get service type:
        # assemble stop script path:
        # assemble stop command:
        # run stop command:
        # command succeeded: return true
        # command failed: return false and error
        pass

    def upload_final_logs(self):
        """Package remaining logs and wait for upload."""
        # run command and wait for it to finish:
        # sleep (a magical) 10 seconds:
        pass

    def shutdown_instance(self):
        """Poweroff the instance."""
        # run shutdown command with a delay:
        pass


def main():
    # parse arguments:
    # read instance and module information:
    # init StopInstanceWorkers:
    # start workers:
    # wait for workers to join:
    # update instance status based on result:
    pass


if __name__ == "__main__":
    main()
