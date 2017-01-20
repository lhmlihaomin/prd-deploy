from __future__ import unicode_literals

from django.db import models

from awscredentialmgr.models import AWSProfile, AWSRegion
from boto3helper.tags import get_value_by_key

class AWSResource(models.Model):
    profile = models.ForeignKey(AWSProfile, on_delete=models.CASCADE, default=None, null=True)
    region = models.ForeignKey(AWSRegion, on_delete=models.CASCADE, default=None, null=True)
    name = models.CharField(max_length=500)
    resource_id = models.CharField(max_length=500)
    resource_type = models.CharField(max_length=100)
    arn = models.CharField(max_length=500, default=None, blank=True, null=True)
    parent = models.ForeignKey('self',
                               on_delete=models.CASCADE,
                               default=None,
                               null=True,
                               blank=True)

    def __str__(self):
        return "['%s', '%s']"%(self.name, self.resource_id)

    def as_option(self):
        return [self.name, self.resource_id]

    @staticmethod
    def get_image_version(image_name):
        pattern = "([adeprtuv]+)-ami-([0-9a-zA-Z_]+)-([\d\._a-zA-Z]+)-([a-zA-Z\d]+)-(\d{8})"
        m = re.match(pattern, image_name)
        if m is not None:
            return m.groups()[2]
        return ""

    @staticmethod
    def filter_image_by_module(profile, region, module_name):
        pattern = "([adeprtuv]+)-ami-%s-([\d\._a-zA-Z]+)-([a-zA-Z\d]+)-(\d{8})"%(module_name,)
        ret = []
        resources = AWSResource.objects.filter(
            profile=profile,
            region=region,
            name__contains=module_name
        )
        for r in resources:
            m = re.match(pattern, r.name)
            if m is not None:
                #version = m.groups()[1]
                #ret.append([r, version])
                ret.append(r)
        return ret

    @staticmethod
    def to_dict(obj):
        d = {
            "id": obj.id,
            "profile": obj.profile.name,
            "region": obj.region.name,
            "name": obj.name,
            "resource_id": obj.resource_id,
            "resource_type": obj.resource_type,
            "arn": obj.arn,
            "parent": "N/A"
        }
        if obj.parent is not None:
            d.update({"parent": obj.parent.name})
        return d


class AWSResourceHandler(object):
    def __init__(self, account_id, boto3_session):
        self.account_id = account_id
        self.session = boto3_session

    def _tag_value(self, obj, key):
        if obj.tags is None:
            return ""
        for tag in obj.tags:
            if tag['Key'].lower() == key.lower():
                return tag['Value']
        return ""

    def _name_tag(self, obj):
        return self._tag_value(obj, 'name')

    def update_images(self):
        self.images = []
        res = self.session.resource("ec2")
        for image in res.images.filter(Owners=[self.account_id]):
            self.images.append([image.name, image.id, "image", None, None])
        for image in res.images.filter(ExecutableUsers=[self.account_id]):
            self.images.append([image.name, image.id, "image", None, None])
        return self.images

    def update_key_pairs(self):
        self.key_pairs = []
        res = self.session.resource("ec2")
        for key_pair in res.key_pairs.all():
            self.key_pairs.append([key_pair.name, key_pair.name, "key_pair", None, None])
        return self.key_pairs

    def update_instance_profiles(self):
        self.instance_profiles = []
        res = self.session.resource("iam")
        for instance_profile in res.instance_profiles.all():
            self.instance_profiles.append([
                instance_profile.name,
                instance_profile.name,
                "instance_profile",
                instance_profile.arn,
                None
            ])
        return self.instance_profiles

    def update_vpcs(self):
        self.vpcs = []
        res = self.session.resource("ec2")
        for vpc in res.vpcs.all():
            self.vpcs.append([self._name_tag(vpc), vpc.id, "vpc", None, None])
        return self.vpcs

    def update_subnets(self):
        self.subnets = []
        res = self.session.resource("ec2")
        for subnet in res.subnets.all():
            self.subnets.append([
                self._name_tag(subnet),
                subnet.id,
                'subnet',
                None,
                subnet.vpc_id
            ])
        return self.subnets

    def update_security_groups(self):
        self.security_groups = []
        res = self.session.resource("ec2")
        for sg in res.security_groups.all():
            self.security_groups.append([
                sg.group_name,
                sg.id,
                'security_group',
                None,
                sg.vpc_id
            ])
        return self.security_groups

    def update_server_certificates(self):
        self.server_certificates = []
        res = self.session.resource("iam")
        for cert in res.server_certificates.all():
            self.server_certificates.append([
                cert.name,
                cert.name,
                'server_certificate',
                cert.server_certificate_metadata['Arn'],
                None
            ])
        return self.server_certificates

    def update_all(self):
        self.update_images()
        self.update_key_pairs()
        self.update_instance_profiles()
        self.update_vpcs()
        self.update_subnets()
        self.update_security_groups()
        self.update_server_certificates()


class NTPServerDefinition(models.Model):
    vpc_id = models.CharField(max_length=500)
    address = models.CharField(max_length=1000)

