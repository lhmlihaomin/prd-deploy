import re
import json

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from awscredentialmgr.models import AWSProfile, AWSRegion
from ec2mgr.models import EC2Instance

class Module(models.Model):
    """An online module (cluster)"""
    name = models.CharField(max_length=1000)
    profile = models.ForeignKey(AWSProfile)
    region = models.ForeignKey(AWSRegion)

    current_version = models.CharField(max_length=500)
    previous_version = models.CharField(max_length=500)
    is_online_version = models.BooleanField(default=False)
    
    instance_count = models.IntegerField()
    configuration = models.TextField()
    load_balancer_names = models.CharField(max_length=1000)

    instances = models.ManyToManyField(EC2Instance, related_name='modules', blank=True)
    # type of this module. 
    # available types are: (java, tomcat, other)
    service_type = models.CharField(max_length=500, default="java")

    def __str__(self):
        return self.display_name

    def __unicode__(self):
        return unicode(self.display_name)

    def to_dict(self):
        return {
            'name': self.name,
            'current_version': self.current_version,
            'previous_version': self.previous_version,
            'is_online_version': self.is_online_version,
            'instance_count': self.instance_count,
            'load_balancer_names': self.load_balancer_names
        }

    @property
    def display_name(self):
        """Return something like 'prd-appserver-1.2.3-use1'."""
        return "%s-%s-%s-%s"%(self.environ, 
                              self.name, 
                              self.current_version, 
                              self.region.tag_name)
        
    @property
    def version(self):
        return self.current_version

    @property
    def previous_module(self):
        try:
            return Module.objects.get(
                profile=self.profile,
                region=self.region,
                name=self.name,
                current_version=self.previous_version
            )
        except:
            return None

    def set_online_version(self):
        """Set self as online_version and any other not."""
        for module in Module.objects.filter(
            profile=self.profile,
            region=self.region,
            name=self.name
        ).exclude(
            current_version=self.current_version
        ):
            module.is_online_version = False
            module.save()
        self.is_online_version=True
        self.save()

    def get_previous_module(self):
        return Module.objects.get(
            profile=self.profile,
            region=self.region,
            name=self.name,
            current_version=self.previous_version
        )

    @property
    def previous_module(self):
        return self.get_previous_module()

    def ami_version_match(self):
        """check if current_version matches with AMI version number"""
        pattern = "([adefmprtuv]+)-ami-([a-zA-Z0-9_]+)-([\d\._a-zA-Z]+)-([a-zA-Z\d]+)-(\d{8})"
        try:
            content_dict = json.loads(self.configuration)
            m = re.match(pattern, content_dict['image'][0])
            if m is not None:
                version = m.groups()[2]
                if version == self.current_version:
                    return True
        except:
            return False
        return False

    @property
    def environ(self):
        return self.profile.instance_prefix
        """
        if self.profile.name.endswith("alpha"):
            return "dev"
        elif self.profile.name.endswith("beta"):
            return "uat"
        elif self.profile.name.endswith("prd"):
            return "prd"
        """

    @property
    def instance_name_prefix(self):
        """Construct EC2 instance name prefix"""
        if not self.ami_version_match():
            raise Exception("Image and module version not match.")
        return "-".join([self.environ, self.name, self.current_version, \
            self.region.tag_name])

    @property
    def content(self):
        return self.configuration

    @property
    def healthy_instance_count(self):
        """an instance is considered healthy if it's RUNNING AND OK"""
        c = 0
        for ec2instance in self.instances.all():
            if ec2instance.running_state == "running" and \
                    ec2instance.service_status == "ok":
                c += 1
        return c

    @property
    def unhealthy_instance_count(self):
        c = 0
        for ec2instance in self.instances.all():
            if ec2instance.running_state != "running" or \
                    ec2instance.service_status != "ok":
                c += 1
        return c

    @property
    def launch_count(self):
        """how many instances are needed to fill the gap"""
        return self.instance_count - self.healthy_instance_count


    def check_ec2_status(self):
        """True healthy count is no less than required count"""
        if self.healthy_instance_count >= self.instance_count:
            return True
        return False


    def check_single_elb_status(self, lbname):
        """True if all ELB instances are of this module and InService"""
        healthy_instances = self.instances.filter(running_state="running", service_status="ok")
        instance_ids = [ec2instance.instance_id for ec2instance in healthy_instances]
        s = self.profile.get_session(self.region)
        c = s.client('elb')
        resp = c.describe_instance_health(LoadBalancerName=lbname)
        states = resp['InstanceStates']
        for state in states:
            if state['InstanceId'] not in instance_ids:
                return False
            if state['State'] != "InService":
                return False
        return True

    def check_elb_status(self):
        """True if all elb status are all True"""
        if len(self.load_balancer_names) == 0:
            return True
        lbnames = self.load_balancer_names.split(",")
        lbnames = [lbname.strip() for lbname in lbnames]
        for lbname in lbnames:
            if not self.check_single_elb_status(lbname):
                return False
        return True

    def mark_instances_for_stopping(self):
        ret = {}
        for ec2instance in self.instances.all():
            ec2instance.service_status = "to_stop"
            ec2instance.save()
            ret.update({ec2instance.instance_id: True})
        return ret

    
class UpdateStep(models.Model):
    #update_plan = models.ForeignKey(UpdatePlan)
    sequence = models.IntegerField()
    module = models.ForeignKey(Module)
    #previous_module = models.ForeignKey(Module, related_name="+")
    start_time = models.DateTimeField()
    finished = models.BooleanField(default=False)
    ec2_finished = models.BooleanField(default=False)
    elb_finished = models.BooleanField(default=False)

    ec2_launched = models.BooleanField(default=False)
    elb_registered = models.BooleanField(default=False)

    def __str__(self):
        return "%d: %s"%(self.sequence, self.module.__str__())

    def set_finished(self):
        if len(self.module.load_balancer_names) == 0:
            self.elb_finished = True
        if self.ec2_finished and self.elb_finished:
            self.finished = True
            self.save()
        else:
            raise Exception("Cannot set step as finished.")

    def check_ec2_finished(self):
        if self.module.check_ec2_status():
            self.ec2_finished = True
            self.save()
            return True
        return False

    def check_elb_finished(self):
        if self.module.check_elb_status():
            self.elb_finished = True
            self.save()
            return True
        return False

    def check_finished(self):
        if not self.check_ec2_finished():
            return (False, "Not enough healthy EC2 instances.")
        if not self.check_elb_finished():
            return (False, "ELB tasks not finished.")
        return (True, "")
        


class UpdatePlan(models.Model):
    # meta fields:
    project_name = models.CharField(max_length=500)
    project_code = models.CharField(max_length=500)
    project_leader = models.CharField(max_length=500)
    note = models.TextField()
    # update procedure:
    steps = models.ManyToManyField(UpdateStep, related_name="update_plan")
    start_time = models.DateTimeField(default=timezone.now)
    finished = models.BooleanField(default=False)
    error = models.BooleanField(default=False)

    def __str__(self):
        return "%s: %s"%(self.project_code, self.project_name)

    def __unicode__(self):
        return unicode(self.__str__())

    def get_current_step(self):
        """Find the first `unfinished` step"""
        current_step = None
        for step in self.steps.all():
            if not step.finished:
                current_step = step
                break
        return current_step



class UpdateActionLog(models.Model):
    # Who:
    user = models.ForeignKey(User)
    # When:
    timestamp = models.DateTimeField(auto_now_add=True)
    # Where:
    source_ip = models.CharField(max_length=200)
    # What:
    update_plan = models.ForeignKey(UpdatePlan, blank=True, null=True)
    update_step = models.ForeignKey(UpdateStep, blank=True, null=True)
    action = models.CharField(max_length=500)
    # How (additional arguments):
    ## e.g. 
    args = models.TextField(blank=True)
    # Result:
    ## if succeeded: instance_ids, elb_names, etc.
    ## if failed: exception, note, etc.
    result = models.TextField(blank=True)

    def __str__(self):
        return "UpdateActionLog"

    def __unicode__(self):
        return unicode(self.__str__())

    @classmethod
    def create_new_log(cls, user, source_ip, update_plan, update_step, action="", args="", result=""):
        return cls(
            user=user,
            source_ip=source_ip,
            update_plan=update_plan,
            update_step=update_step,
            action=action,
            args=args,
            result=result
        )

    @classmethod
    def create(cls, request, update_plan=None, update_step=None, action="", args="", result=""):
        return cls(
            user = request.user,
            source_ip = request.META.get('REMOTE_ADDR'),
            update_plan = update_plan,
            update_step = update_step,
            action = action,
            args = args,
            result = result
      ) 

    def set_result(self, result, message=""):
        self.result = json.dumps((result, message))

