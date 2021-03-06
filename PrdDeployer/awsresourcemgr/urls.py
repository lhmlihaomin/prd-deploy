from django.conf.urls import include, url

from awsresourcemgr import views

urlpatterns = [
    url(
        r'update_resources/(?P<profile_name>[a-zA-Z0-9-]+)/(?P<region_name>[a-zA-Z0-9-]+)/(?P<resource_type>.+)/$',
        views.update_resources,
        name="update_resources"
    ),
    url(
        r'resources/(?P<profile_name>[a-zA-Z0-9-]+)/(?P<region_name>[a-zA-Z0-9-]+)/$',
        views.resources,
        name="resources"
    ),
]
