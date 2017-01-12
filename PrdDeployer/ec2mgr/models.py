from django.db import models

from boto3helper.tags import get_resource_name

class EC2Instance(models.Model):
    name = models.CharField(max_length=500)
    instance_id = models.CharField(max_length=500, default="")
    private_ip_address = models.CharField(max_length=100, default="")
    username = models.CharField(max_length=100, default="ubuntu")
    key_pair = models.CharField(max_length=100, default="")
    running_state = models.CharField(max_length=100, default="")
    service_status = models.CharField(max_length=100, default="")
    note = models.TextField(default="")
    instance_created = models.BooleanField(default=False)
    instance_tags_added = models.BooleanField(default=False)
    volume_tags_added = models.BooleanField(default=False)

    def load_boto3_instance(self, instance):
        """Get info from a boto3.ec2.Instance"""
        self.name = get_resource_name(instance)
        self.instance_id = instance.id
        self.private_ip_address = instance.private_ip_address
        self.key_pair = instance.key_pair.name
        self.running_state = instance.state['Name']
        self.service_status = ""
        self.note = ""