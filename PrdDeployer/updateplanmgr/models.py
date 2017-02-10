import re
import json

from django.db import models
from django.utils import timezone
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

    instances = models.ManyToManyField(EC2Instance)
    # type of this module. 
    # available types are: (java, tomcat, other)
    service_type = models.CharField(max_length=500, default="java")

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
        pattern = "([adeprtuv]+)-ami-([a-zA-Z0-9_]+)-([\d\._a-zA-Z]+)-([a-zA-Z\d]+)-(\d{8})"
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
        if self.profile.name.endswith("alpha"):
            return "dev"
        elif self.profile.name.endswith("beta"):
            return "uat"
        elif self.profile.name.endswith("prd"):
            return "prd"

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
        return self.instance_count - self.healthy_instance_count

    
class UpdateStep(models.Model):
    #update_plan = models.ForeignKey(UpdatePlan)
    sequence = models.IntegerField()
    module = models.ForeignKey(Module)
    #previous_module = models.ForeignKey(Module, related_name="+")
    start_time = models.DateTimeField()
    finished = models.BooleanField(default=False)
    ec2_finished = models.BooleanField(default=False)
    elb_finished = models.BooleanField(default=False)

    def set_finished(self):
        if len(self.module.load_balancer_names) == 0:
            self.elb_finished = True
        if self.ec2_finished and self.elb_finished:
            self.finished = True
            self.save()
        else:
            raise Exception("Cannot set step as finished.")


class UpdatePlan(models.Model):
    # meta fields:
    project_name = models.CharField(max_length=500)
    project_code = models.CharField(max_length=500)
    project_leader = models.CharField(max_length=500)
    note = models.TextField()
    # update procedure:
    steps = models.ManyToManyField(UpdateStep)
    start_time = models.DateTimeField(default=timezone.now)
    finished = models.BooleanField(default=False)

