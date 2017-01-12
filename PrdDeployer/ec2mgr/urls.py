from django.conf.urls import include, url

from ec2mgr import views

urlpatterns = [
    url(r'^sync/(?P<profile_name>[a-zA-Z0-9-]+)/(?P<region_name>[a-zA-Z0-9-]+)/$', views.sync_instances, name="sync_instances"),
    
]
