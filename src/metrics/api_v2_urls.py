from django.conf.urls import url
import api_v2_views

from django.conf.urls import url
import api_v2_views as views

urlpatterns = [
    # /metrics/{type}/{id}/{metric}
    url(r'(?P<type>article)/(?P<id>\d+)/(?P<metric>(citations|downloads|page-views))$', api_v2_views.metrics),
]
