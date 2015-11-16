from collections import OrderedDict
from datetime import datetime, timedelta
import elife_ga_metrics as ga_metrics
from elife_hw_metrics import core as hw_metrics
from elife_ga_metrics import bulk, utils
from django.conf import settings
import models
from django.db import transaction
from elife_ga_metrics.core import ymd
from django import db
import logging

LOG = logging.getLogger(__name__)
LOG.level = logging.DEBUG

def subdict(d, kl):
    return {k:v for k, v in d.items() if k in kl}

def exsubdict(d, kl):
    return {k:v for k, v in d.items() if k not in kl}

def format_dt_pair(dt_pair):
    """the database expects values in yyyy-mm or yyyy-mm-dd format.
    this function takes a pair of datetime objects and returns a pair of
    `(type, datestring)`, for example `('day', '2015-01-31')` for daily
    of `('month', '2015-01')` for monthly"""
    from_date, to_date = dt_pair
    if from_date == to_date:
        # daily, looks like 2015-01-01, 2015-01-01
        return models.DAY, from_date
    if from_date[-2:] == '01' and to_date[-2:] in ['31', '30', '28']:
        # monthly, looks 2015-01-01, 2015-01-31
        return models.MONTH, from_date[:7]
    raise ValueError("given dtpair %r but it doesn't look like a daily or monthly result!" % dt_pair)

def insert_row(data):
    row = exsubdict(data, 'doi')
    
    article_obj, created = models.Article.objects.get_or_create(doi=data['doi'])
    row['article'] = article_obj
    
    try:
        # fetch the metric if it exists
        sd = subdict(row, ['article', 'date', 'period', 'source'])
        metric = models.Metric.objects.get(**sd)
        try:
            # it exists!
            # now we must test it's data for changes
            models.Metric.objects.get(**row)
            LOG.debug('metric found and data is exact %r, skipping', sd)
        except models.Metric.DoesNotExist:
            # data has changed!
            # this happens when importing partial daily/monthly stats            
            LOG.debug('metric found and data has changed from %r to %r. updating', metric.pdf, data['pdf'])
            [setattr(metric, attr, val) for attr, val in row.items()]
            metric.save()

    except models.Metric.DoesNotExist:
        metric = models.Metric(**row)
        metric.save()
        LOG.info('created metric %r', metric)

    return metric


@transaction.atomic
def import_hw_metrics(metrics_type='daily', from_date=None, to_date=None):
    "import metrics from Highwire between the two given dates or from inception"
    assert metrics_type in ['daily', 'monthly'], 'metrics type must be either "daily" or "monthly"'
    if not from_date:
        # HW metrics go back further than GA metrics
        from_date = hw_metrics.INCEPTION
    if not to_date:
        to_date = datetime.now()

    def create_hw_row(data):
        "wrangles the data into something that can be inserted directly"
        data['digest'] = 0
        data['source'] = models.HW
        return insert_row(data)
    
    # not going to be delicate about this. just import all we can find.
    results = hw_metrics.metrics_between(from_date, to_date, metrics_type)
    for dt, items in results.items():
        map(create_hw_row, items)

def import_ga_metrics(metrics_type='daily', from_date=None, to_date=None, use_cached=True, use_only_cached=False):
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
    results = f[metrics_type](table_id, from_date, to_date, use_cached, use_only_cached)
    
    def create_row(doi, dt_pair, views, downloads):
        "wrangles the data into a format suitable for `insert_row`"
        if not views:
            views = {
                'full': 0,
                'abstract': 0,
                'digest': 0,
            }
        views['pdf'] = downloads or 0
        views['doi'] = doi
        views['source'] = models.GA
        row = dict(zip(['period', 'date'], format_dt_pair(dt_pair)))
        row.update(views)
        return row

    # ok, this is a bit hacky, but on very long runs (when we do a full import for example) the
    # kernel will kill the process for being a memory hog
    #@transaction.atomic
    def commit_rows(queue, force=False):
        "commits the objects in the queue every time it hits 1000 objects or is told otherwise"
        if len(queue) == 1000 or force:
            LOG.info("committing %s objects to db", len(queue))
            with transaction.atomic():
                map(insert_row, queue)
            queue = []
            db.reset_queries()
            # NOTE: this problem isn't solved, it's still leaking memory
            
        return queue

    # whatever mode we're in, ensure debug is off for import
    old_setting = settings.DEBUG
    settings.DEBUG = False

    queue = []
    for dt_pair, metrics in results.items():
        downloads = metrics['downloads']
        views = metrics['views']
        
        doi_list = set(views.keys()).union(downloads.keys())
        for doi in doi_list:
            queue.append(create_row(doi, dt_pair, views.get(doi), downloads.get(doi)))
            queue = commit_rows(queue)

    # commit any remaining
    commit_rows(queue, force=True)
    settings.DEBUG = old_setting


#
#
#

from rest_framework import serializers as szr

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
    date_list = utils.dt_month_range(from_date, to_date) # ll: [(2013-01-01, 2013-01-31), (2013-02-01, 2013-02-28), ...]
    date_list = [ymd(i[0])[:7] for i in date_list] # ll:  [2013-01, 2013-02, 2013-03]
    return models.Metric.objects \
      .filter(article__doi__iexact=doi) \
      .filter(source=source) \
      .filter(period=models.MONTH) \
      .filter(date__in=date_list)

def monthly_since_ever(doi, source=models.GA):
    #the_beginning = ga_metrics.core.VIEWS_INCEPTION
    the_beginning = hw_metrics.INCEPTION
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
