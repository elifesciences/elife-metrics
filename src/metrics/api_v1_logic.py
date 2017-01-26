from collections import OrderedDict
from datetime import datetime, timedelta
from ga_metrics import utils as ga_utils
from ga_metrics.core import ymd
from django.conf import settings
import models
import logging
from rest_framework import serializers as szr

LOG = logging.getLogger(__name__)

class MetricSerializer(szr.ModelSerializer):
    class Meta:
        exclude = ('article', 'id', 'period', 'source')
        model = models.Metric
#
#
#

def daily(doi, from_date, to_date, source=models.GA):
    return models.Metric.objects \
        .filter(article__doi__iexact=doi) \
        .filter(source=source) \
        .filter(period=models.DAY) \
        .filter(date__gte=ymd(from_date), date__lte=ymd(to_date)) # does this even work with charfields??

def group_daily_by_date(daily_results):
    # assume there is a single daily result, like for a specific doi
    def grouper(iterable, func):
        results = OrderedDict({})
        for item in iterable:
            key = func(item)
            del item['date']
            results[key] = dict(item)
        return results
    return grouper(MetricSerializer(daily_results, many=True).data, lambda obj: obj['date'])

def daily_last_n_days(doi, days=30, source=models.GA):
    yesterday = datetime.now() - timedelta(days=1)
    n_days_ago = datetime.now() - timedelta(days=days)
    return daily(doi, n_days_ago, yesterday, source)

def monthly(doi, from_date, to_date, source=models.GA):
    """returns monthly metrics for the given article for the month
    starting in `from_date` to the month ending in `to_date`"""
    # because we're not storing dates, but rather a representation of a date
    date_list = ga_utils.dt_month_range(from_date, to_date) # ll: [(2013-01-01, 2013-01-31), (2013-02-01, 2013-02-28), ...]
    date_list = [ymd(i[0])[:7] for i in date_list] # ll:  [2013-01, 2013-02, 2013-03]
    return models.Metric.objects \
        .filter(article__doi__iexact=doi) \
        .filter(source=source) \
        .filter(period=models.MONTH) \
        .filter(date__in=date_list)

def monthly_since_ever(doi, source=models.GA):
    #the_beginning = ga_metrics.core.VIEWS_INCEPTION
    # BROKEN
    the_beginning = settings.INCEPTION
    return monthly(doi, the_beginning, datetime.now(), source)

def group_monthly_results(results):
    def grouper(iterable, func):
        results = OrderedDict({})
        for item in iterable:
            key = func(item)
            del item['date']
            results[key] = dict(item)
        return results
    return grouper(MetricSerializer(results, many=True).data, lambda obj: obj['date'])
