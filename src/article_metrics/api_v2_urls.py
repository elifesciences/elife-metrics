from django.conf.urls import re_path
from . import api_v2_views as views

app_name = 'article_metrics'
urlpatterns = ([
    # article-level metrics
    re_path(r'^ping$', views.ping, name='ping'),
    re_path(r'^article/(?P<msid>\d+)/(?P<metric>(citations|downloads|page-views))$', views.article_metrics, name='alm'),

    re_path(r'^article/(?P<msid>\d+)/summary$', views.summary, name='article-summary'),
    # lsh@2022-03-04: disabled in favour of views.summary2. views.summary still ok for individual articles.
    #re_path(r'^article/summary$', views.summary, name='summary'),
    re_path(r'^article/summary$', views.summary2, name='summary'),

], app_name)
