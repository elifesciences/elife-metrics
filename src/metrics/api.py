from django.conf.urls import include, url
import views
import operator

urlpatterns_meta = [
    url(r'docs/', include('rest_framework_swagger.urls')),
]

urlpatterns_v1 = [
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/$', views.api_article_metrics, name='api-article-metrics'),
]

urlpatterns_v2 = [
    # ...
]

urlpatterns = reduce(operator.add, [urlpatterns_meta, urlpatterns_v1, urlpatterns_v2])
