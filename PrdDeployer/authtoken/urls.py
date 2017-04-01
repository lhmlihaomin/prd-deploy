from django.conf.urls import url

from authtoken import views

urlpatterns = [
    url(r'^usertoken/(?P<user_id>\d+)/$', views.user_token, name='user_token'),
    url(r'^deletetoken/(?P<user_id>\d+)/(?P<token_id>\d+)/$', views.delete_token, name='delete_token'),
    url(r'^toggletoken/(?P<user_id>\d+)/(?P<token_id>\d+)/$', views.toggle_token, name='toggle_token'),
    url(r'^authtest/$', views.authtest, name='authtest'),
]
