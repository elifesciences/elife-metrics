from collections import OrderedDict
from datetime import datetime, timedelta
import elife_ga_metrics as ga_metrics
from elife_ga_metrics import bulk
from django.conf import settings
import models
from django.db import transaction
from elife_ga_metrics.core import ymd

import logging

LOG = logging.getLogger(__name__)
LOG.level = logging.DEBUG

def subdict(d, kl):
    return {k:v for k, v in d.items() if k in kl}

def format_dt_pair(dt_pair):
    from_date, to_date = dt_pair
    if from_date == to_date:
        # daily, looks like 2015-01-01, 2015-01-01
        return models.DAY, from_date
    if from_date[-2:] == '01' and to_date[-2:] in ['31', '30', '28']:
        # monthly, looks 2015-01-01, 2015-01-31
        return models.MONTH, from_date[:7]
    raise ValueError("given dtpair %r but it doesn't look like a daily or monthly result!" % dt_pair)

def create_row(doi, dt_pair, views, downloads):
    "creates a row from the given data suitable for inserting into the metrics table"
    if not views:
        views = {
            'full': 0,
            'abstract': 0,
            'digest': 0
        }
    views['pdf'] = downloads or 0

    row = dict(zip(['period', 'date'], format_dt_pair(dt_pair)))
    row.update(views)
    return row

@transaction.atomic
def import_ga_metrics(metrics_type='daily', from_date=None, to_date=None):
    "import metrics from GA between the two given dates or from inception"
    assert metrics_type in ['daily', 'monthly'], 'metrics type must be either "daily" or "monthly"'
    
    table_id = 'ga:%s' % settings.GA_TABLE_ID
    the_beginning = ga_metrics.core.VIEWS_INCEPTION
    yesterday = datetime.now() - timedelta(days=1)

    if not from_date:
        from_date = the_beginning

    if not to_date:
        # don't import today's partial results. they're available but lets wait until tomorrow
        to_date = yesterday

    f = {
        'daily': bulk.daily_metrics_between,
        'monthly': bulk.monthly_metrics_between,
    }
    results = f[metrics_type](table_id, from_date, to_date)
    
    for dt_pair, metrics in results.items():
        downloads = metrics['downloads']
        views = metrics['views']
        
        doi_list = set(views.keys()).union(downloads.keys())
        for doi in doi_list:
            
            row = create_row(doi, dt_pair, views.get(doi), downloads.get(doi))
            article_obj, created = models.Article.objects.get_or_create(doi=doi)
            row['article'] = article_obj
            sd = subdict(row, ['article', 'date', 'period'])
            try:
                models.GAMetric.objects.get(**sd)
                LOG.debug('metric found for %r, skipping', sd)
                # update here if necessary
            except models.GAMetric.DoesNotExist:
                obj = models.GAMetric(**row)
                obj.save()
                LOG.info('created metric %r',obj)

#
#
#

from rest_framework import serializers as szr

class MetricSerializer(szr.ModelSerializer):
    class Meta:
        exclude = ('article', 'id', 'period')
        model = models.GAMetric


#
#
#

def daily(doi, from_date, to_date):
    return models.GAMetric.objects \
      .filter(article__doi__iexact=doi) \
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

def daily_last_n_days(doi, days=30):
    yesterday = datetime.now() - timedelta(days=1)
    n_days_ago = datetime.now() - timedelta(days=days)
    return daily(doi, n_days_ago, yesterday)

def monthly(doi, from_date, to_date):
    """returns monthly metrics for the given article for the month
    starting in `from_date` to the month ending in `to_date`"""
    # because we're not storing dates, but rather a representation of a date
    date_list = bulk.dt_month_range(from_date, to_date) # ll: [(2013-01-01, 2013-01-31), (2013-02-01, 2013-02-28), ...]
    date_list = [ymd(i[0])[:7] for i in date_list] # ll:  [2013-01, 2013-02, 2013-03]
    return models.GAMetric.objects \
      .filter(article__doi__iexact=doi) \
      .filter(period=models.MONTH) \
      .filter(date__in=date_list)

def monthly_since_ever(doi):
    the_beginning = ga_metrics.core.VIEWS_INCEPTION
    return monthly(doi, the_beginning, datetime.now())

def group_monthly_results(results):
    def grouper(iterable, func):
        results = OrderedDict({})
        for item in iterable:
            key = func(item)
            del item['date']
            results[key] = dict(item)
        return results    
    return grouper(MetricSerializer(results, many=True).data, lambda obj: obj['date'])
    
