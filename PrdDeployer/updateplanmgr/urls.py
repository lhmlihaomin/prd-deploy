from django.conf.urls import include, url

from updateplanmgr import views
from updateplanmgr import ajax_views
from updateplanmgr import api_views

urlpatterns = [
    #url(r'^v1/$', views.v1),
    #url(r'^v2/(?P<profile_name>[a-zA-Z0-9-]+)/(?P<region_name>[a-zA-Z0-9-]+)/$', views.v2),
    url(r'^$', views.index, name="index"),
    url(r'^modules/(?P<profile_name>[a-zA-Z0-9-]+)/(?P<region_name>[a-zA-Z0-9-]+)/$', views.modules, name='modules'),
    url(r'^edit_module_json/(?P<module_id>\d+)/$', views.edit_module_json, name='edit_module_json'),
    url(r'^updateplans/$', views.updateplans, name='updateplans'),
    url(r'^updateplan/(?P<plan_id>\d+)/$', views.updateplan, name='updateplan'),
    url(r'^updateplan/(?P<plan_id>\d+)/kickdevices/(?P<step_id>\d+)/$', views.kick_devices, name='kickdevices'),
    url(r'^new_updateplan/$', views.new_updateplan, name='new_updateplan'),
    url(r'^new_module/$', views.new_module, name='new_module'),
    url(r'^fix_service_types/$', views.fix_service_types, name='fix_service_types'),
    url(r'^instances_summary/(?P<plan_id>\d+)/$', views.instances_summary, name='instances_summary'),
    url(r'^elb_summary/(?P<plan_id>\d+)/$', views.elb_summary, name='elb_summary'),
    url(r'actionlogs/(?P<plan_id>\d+)/$', views.actionlogs, name='actionlogs'),
    url(r'^edit_module/(?P<module_id>\d+)/$', views.edit_module, name='edit_module'),

    # ajax views:
    url(r'ajax/run_module_ec2/', ajax_views.run_module_ec2, name='ajax.run_module_ec2'),
    url(r'ajax/add_module_ec2_tags/', ajax_views.add_module_ec2_tags, name='ajax.add_module_ec2_tags'),
    url(r'ajax/add_module_volume_tags/', ajax_views.add_module_volume_tags, name='ajax.add_module_volume_tags'),
    url(r'ajax/stop_module_ec2/', ajax_views.stop_module_ec2, name='ajax.stop_module_ec2'),
    url(r'ajax/stop_module_previous_ec2/', ajax_views.stop_module_previous_ec2, name='ajax.stop_module_previous_ec2'),
    url(r'ajax/reg_module_elb/', ajax_views.reg_module_elb, name='ajax.reg_module_ec2'),
    url(r'ajax/dereg_module_elb/', ajax_views.dereg_module_elb, name='ajax.dereg_module_ec2'),
    url(r'ajax/check_module_elb_health/', ajax_views.check_module_elb_health, name='ajax.check_module_elb_health'),
    url(r'ajax/disable_module_alarm/', ajax_views.disable_module_alarm, name='ajax.disable_module_alarm'),

    url(r'ajax/deregister_connectors/', ajax_views.deregister_connectors, name='ajax.deregister_connectors'),
    url(r'ajax/get_connector_device_numbers/', ajax_views.get_connector_device_numbers, name='ajax.get_connector_device_numbers'),
    url(r'ajax/init_connector_close_all/', ajax_views.init_connector_close_all, name='ajax.init_connector_close_all'),

    url(r'ajax/finish_step/', ajax_views.finish_step, name='ajax.finish_step'),

    url(r'api/new_updateplan/', api_views.new_updateplan, name='api.new_updateplan'),
]
