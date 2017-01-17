from os.path import join
from django.conf import settings
from django.shortcuts import get_object_or_404
from annoying.decorators import render_to
import logic, models

from rest_framework.decorators import api_view
from rest_framework.response import Response

@render_to('metrics/index.html')
def index(request):
    return {
        'readme': open(join(settings.PROJECT_DIR, 'README.md'), 'r').read()
    }

#
# API
#

@api_view(['GET'])
def api_article_metrics(request, doi):
    get_object_or_404(models.Article, doi=doi)
    return Response({
        doi: {
            'daily': logic.group_daily_by_date(logic.daily_last_n_days(doi, 30)),
            'monthly': logic.group_monthly_results(logic.monthly_since_ever(doi)),
        }
    })

@api_view(['GET'])
def api_article_metrics_mixed_source(request, doi):
    get_object_or_404(models.Article, doi=doi)
    return Response({
        models.GA: {
            doi: {
                'daily': logic.group_daily_by_date(logic.daily_last_n_days(doi, 30)),
                'monthly': logic.group_monthly_results(logic.monthly_since_ever(doi)),
            },
        },
        models.HW: {
            doi: {
                'daily': logic.group_daily_by_date(logic.daily_last_n_days(doi, 30, models.HW)),
                'monthly': logic.group_monthly_results(logic.monthly_since_ever(doi, models.HW)),
            },
        }
    })
