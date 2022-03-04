from django.conf.urls import url
from . import api_v2_views as views

app_name = 'article_metrics'
urlpatterns = ([
    # article-level metrics
    url(r'^ping$', views.ping, name='ping'),
    url(r'^article/(?P<msid>\d+)/(?P<metric>(citations|downloads|page-views))$', views.article_metrics, name='alm'),

    url(r'^article/(?P<msid>\d+)/summary$', views.summary, name='article-summary'),
    # lsh@2022-03-04: disabled in favour of views.summary2. views.summary still ok for individual articles.
    #url(r'^article/summary$', views.summary, name='summary'),
    url(r'^article/summary$', views.summary2, name='summary2'),

], app_name)
