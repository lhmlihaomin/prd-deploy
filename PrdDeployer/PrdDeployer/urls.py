"""
Definition of urls for PrdDeployer.
"""

from django.conf.urls import include, url
from django.http import HttpResponseRedirect

import updateplanmgr.urls
import awsresourcemgr.urls
import ec2mgr.urls

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from django.contrib.auth.views import login, logout
admin.autodiscover()

urlpatterns = [
    # Examples:
    # url(r'^$', 'PrdDeployer.views.home', name='home'),
    # url(r'^PrdDeployer/', include('PrdDeployer.PrdDeployer.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),

    # updatemgr:
    url(r'^$', lambda r: HttpResponseRedirect('update/'), name="home"),

    url(r'^update/', include(updateplanmgr.urls, namespace='updateplanmgr', app_name='updateplanmgr')),
    # awsresourcemgr:
    url(r'^awsres/', include(awsresourcemgr.urls, namespace='awsresourcemgr', app_name='awsresourcemgr')),
    # ec2mgr:
    url(r'^ec2/', include(ec2mgr.urls, namespace='ec2mgr', app_name='ec2mgr')),

    url(r'accounts/login/', login,
        {'template_name': 'admin/login.html'}),
    url(r'accounts/logout/', logout, name='logout'),
]
