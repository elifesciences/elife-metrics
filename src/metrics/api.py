from rest_framework_swagger.views import get_swagger_view
from django.conf.urls import url
import views
import operator

urlpatterns_meta = [
    url(r'docs/', get_swagger_view(title='Article Store API')),
]

urlpatterns_v1 = [
    url(r'v1/article/hw,ga/(?P<doi>[\.\w]+\/[\.\w]+)/$', views.api_article_metrics_mixed_source, name='api-article-metrics-mixed-source'),
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/$', views.api_article_metrics, name='api-article-metrics'),
]

urlpatterns_v2 = [
    # ...
]

urlpatterns = reduce(operator.add, [urlpatterns_meta, urlpatterns_v1, urlpatterns_v2])
