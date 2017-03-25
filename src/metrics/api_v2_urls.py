from django.conf.urls import url
from . import api_v2_views as views

urlpatterns = [
    # article-level metrics
    url(r'article/(?P<id>\d+)/(?P<metric>(citations|downloads|page-views))$', views.article_metrics, name='alm'),
]
