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
    created_at = models.DateTimeField(auto_now_add=True)
    last_checked_at = models.DateTimeField(blank=True, null=True)
    service_stopped_at = models.DateTimeField(blank=True, null=True)

    vpc_id = models.CharField(max_length=500, default="")


    def __str__(self):
        return self.name

    def __unicode__(self):
        return unicode(self.name)

    def load_boto3_instance(self, instance):
        """Get info from a boto3.ec2.Instance"""
        self.name = get_resource_name(instance)
        self.instance_id = instance.id
        self.private_ip_address = instance.private_ip_address
        self.key_pair = instance.key_pair.name
        self.running_state = instance.state['Name']
        self.service_status = ""
        self.note = ""
        self.vpc_id = instance.vpc_id

    def service_ok(self):
        return self.service_status == "ok"

    def set_not_ready(self):
        self.service_status = "not_ready"
        self.note = "Instance just started."

    @property
    def service_scripts(self):
        module = self.modules.first()
        if module is None:
            raise Exception("Module not found.")
        if module.service_type == 'java':
            service_bin_dir = "/"+"/".join([
                'home',
                self.username,
                '-'.join(['cloud', module.name]),
                '-'.join(['cloud', module.name, module.current_version]),
                'bin'
            ])
            return {
                'start': '/'.join([service_bin_dir, 'start.sh']),
                'stop': '/'.join([service_bin_dir, 'stop.sh']),
                'status': '/'.join([service_bin_dir, 'status.sh']),
            }
        elif module.service_type == 'tomcat':
            tomcat_bin_dir = "/"+"/".join([
                'home',
                self.username,
                '-'.join(['cloud', module.name]),
                'tomcat',
                'bin'
            ])
            service_bin_dir = "/"+"/".join([
                'home',
                self.username,
                '-'.join(['cloud', module.name]),
                '-'.join(['cloud', module.name, module.current_version]),
                'WEB-INF',
                'classes'
            ])
            return {
                'start': '/'.join([tomcat_bin_dir, 'startup.sh']),
                'stop': '/'.join([tomcat_bin_dir, 'shutdown.sh']),
                'status': '/'.join([service_bin_dir, 'status.sh']),
            }
        else:
            raise Exception("Unknown service type: "+module.service_type)

    @property
    def stop_command(self):
        module = self.modules.first()
        if module is None:
            raise Exception("Module not found.")
        if module.service_type == 'java':
            service_bin_dir = "/"+"/".join([
                'home',
                self.username,
                '-'.join(['cloud', module.name]),
                '-'.join(['cloud', module.name, module.current_version]),
                'bin'
            ])
            return "/bin/bash %s/stop.sh"%(service_bin_dir,)
        elif module.service_type == 'tomcat':
            tomcat_bin_dir = "/"+"/".join([
                'home',
                self.username,
                '-'.join(['cloud', module.name]),
                'tomcat',
                'bin'
            ])
            return "cd %s&&/bin/bash ./shutdown.sh"%(tomcat_bin_dir,)
        else:
            raise Exception("Unknown service type: "+module.service_type)
