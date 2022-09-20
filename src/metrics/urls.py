from django.conf.urls import re_path
from . import views, models

page_type_str = '|'.join(models.PAGE_TYPES)

urlpatterns = [
    re_path(r'^api/v2/(?P<ptype>(' + page_type_str + '))/page-views$', views.metrics, name='nam'),
    re_path(r'^api/v2/(?P<ptype>(' + page_type_str + r'))/(?P<pid>\w+)/page-views$', views.metrics, name='nam'),
]
