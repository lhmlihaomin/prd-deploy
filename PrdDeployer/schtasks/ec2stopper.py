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
    instance.last_checked_at = now

if service_status == 'stopped':
    if now - instance.last_checked_at > STOP_THRESHOLD:
        boto3.stop(instance)
        instance.running_state = new_state
        instance.service_status = 'down'
    else:
        do nothing
"""

import time


class EC2Stopper(object):
    pass
