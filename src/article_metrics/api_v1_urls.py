from django.conf.urls import re_path
from . import api_v1_views as views

urlpatterns = [
    re_path(r'^article/hw,ga/(?P<doi>[\.\w]+\/[\.\w]+)/$', views.api_article_metrics_mixed_source, name='api-article-metrics-mixed-source'),
    re_path(r'^article/(?P<doi>[\.\w]+\/[\.\w]+)/$', views.api_article_metrics, name='api-article-metrics'),
]
