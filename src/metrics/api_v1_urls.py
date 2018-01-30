from django.conf.urls import url
from . import api_v1_views as views

urlpatterns = [
    url(r'^article/hw,ga/(?P<doi>[\.\w]+\/[\.\w]+)/$', views.api_article_metrics_mixed_source, name='api-article-metrics-mixed-source'),
    url(r'^article/(?P<doi>[\.\w]+\/[\.\w]+)/$', views.api_article_metrics, name='api-article-metrics'),
]
