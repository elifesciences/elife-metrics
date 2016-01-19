from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^proxy/metrics/api/', include('metrics.api', namespace="proxied")), # integration with upstream api
    url(r'^api/', include('metrics.api')),
    url(r'', include('metrics.urls')),
]
