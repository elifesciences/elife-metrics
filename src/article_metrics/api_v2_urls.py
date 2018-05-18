from django.conf.urls import url
from . import api_v2_views as views

urlpatterns = [
    # article-level metrics
    url(r'^ping$', views.ping, name='ping'),
    url(r'^article/(?P<msid>\d+)/(?P<metric>(citations|downloads|page-views))$', views.article_metrics, name='alm'),

    url(r'^article/(?P<msid>\d+)/summary$', views.summary, name='article-summary'),
    url(r'^article/summary$', views.summary, name='summary'),

]
