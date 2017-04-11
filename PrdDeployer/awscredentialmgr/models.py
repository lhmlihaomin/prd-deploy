from django.db import models
import boto3


class AWSRegion(models.Model):
    name = models.CharField(max_length=500)
    full_name = models.CharField(max_length=500)
    tag_name = models.CharField(max_length=500)

    def __str__(self):
        return self.name
        
    def __unicode__(self):
        return unicode(self.__str__())


class AWSProfile(models.Model):
    name = models.CharField(max_length=500)
    regions = models.ManyToManyField(AWSRegion, related_name="profiles")
    account_id = models.CharField(max_length=500, default="")

    # These two fields shall always be left empty unless not configured in
    # config file ~/.aws/credentials
    aws_access_key_id = models.CharField(max_length=500, default="", blank=True)
    aws_secret_access_key = models.CharField(max_length=500, default="", blank=True)

    def has_region(self, region):
        """Check if region is associated with this profile."""
        return region in self.regions.all()

    def get_session(self, region):
        """Return a boto3 session connected to 'region'."""
        if not self.has_region(region):
            raise Exception("Profile %s cannot connect to region %s"%(self.name, region.full_name))
        return boto3.Session(
            profile_name=self.name,
            region_name=region.name)

    @property
    def env(self):
        return self.name.split('-')[1]
    
