from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^', include('article_metrics.urls')),
    url(r'^', include('metrics.urls')),
]
