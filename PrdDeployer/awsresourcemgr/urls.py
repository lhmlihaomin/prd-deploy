from django.conf.urls import include, url

from awsresourcemgr import views

urlpatterns = [
    url(r'update_resources/(?P<profile_name>[a-zA-Z0-9-]+)/(?P<region_name>[a-zA-Z0-9-]+)/$', views.update_resources),
]
