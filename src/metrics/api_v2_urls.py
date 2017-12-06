from django.conf.urls import url
import api_v2_views as views

urlpatterns = [
    # article-level metrics
    url(r'^ping$', views.ping, name='ping'),
    url(r'^article/(?P<id>\d+)/(?P<metric>(citations|downloads|page-views))$', views.article_metrics, name='alm'),

    #url(r'^article/summary/(?P<id>\d+)$', views.article_summary, name='article-summary'),
    url(r'^article/summary$', views.summary, name='summary'),

]
