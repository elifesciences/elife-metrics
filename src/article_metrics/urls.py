from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'^api/v2/', include('article_metrics.api_v2_urls', namespace='v2')),
    url(r'^api/v1/', include('article_metrics.api_v1_urls')),

    url(r'^$', views.index, name='index'),
]
