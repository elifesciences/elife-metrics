from django.conf.urls import url
from . import views, models

page_type_str = '|'.join(models.PAGE_TYPES)

urlpatterns = [
    url(r'^(?P<ptype>(' + page_type_str + '))/page-views$', views.metrics, name='nam'),
    url(r'^(?P<ptype>(' + page_type_str + '))/(?P<pid>\w+)/page-views$', views.metrics, name='nam'),
]
