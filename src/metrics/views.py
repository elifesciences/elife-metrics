from django.shortcuts import render, get_object_or_404
from annoying.decorators import render_to
import logic, models

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import serializers as szr

@render_to('index.html')
def index(request):
    return {}

@api_view(['GET'])
def api_article_metrics(request, doi):
    artobj = get_object_or_404(models.Article, doi=doi)
    return Response({
        doi: {
            'daily': logic.group_daily_by_date(logic.daily_last_n_days(doi, 30)),
            'monthly': logic.group_monthly_results(logic.monthly_since_ever(doi)),
        }
    })
