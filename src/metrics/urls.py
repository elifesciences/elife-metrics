from django.conf.urls import include, url
from rest_framework_swagger.views import get_swagger_view
import views

urlpatterns = [
    url(r'^api/docs/', get_swagger_view(title='Article Metrics API')),
    url(r'^api/v2/', include('metrics.api_v2_urls', namespace='v2')),
    url(r'^api/v1/', include('metrics.api_v1_urls')),

    url(r'^$', views.index, name='index'),
]
