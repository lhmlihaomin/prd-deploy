# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

class UpdateRunner(object):
    """Get last unfinished step and run update"""
    def __init__(self, plan):
        self.update_plan = plan
        self.get_current_step()

    def get_current_step(self):
        self.current_step = self.update_plan.get_current_step()
        return self.current_step

    def start_new_version(self):
        # run instances:
        # add tags:
        # add volume tags:
        # save instances to db:
        # set start timer:
        # check service status until time out:
        # save result:

    def stop_old_version(self):
        pass
        # disable alarms:
        # stop instances:
        # save result:

    def lb_register_new_version(self):
        pass
        # register instances with each load balancer:
        # check if all instances are in returned list:
        # save result:

    def lb_deregister_old_version(self):
        pass
        # deregister instances from each load balancer:
        # check if none of instances in returned list:
        # save result:

    def run_current_step(self):
        pass
        