from . import models
from metrics.utils import ensure
from metrics.ga_metrics import core as ga_core
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from collections import defaultdict
from django.conf import settings
from datetime import date

DAY, MONTH = 'day', 'month'

def is_pid(pid):
    return isinstance(pid, str) and len(pid) < 256

def is_ptype(ptype):
    return isinstance(ptype, str) and len(ptype) < 256

def is_period(period):
    return period in [MONTH, DAY]

#
#
#

def generate_date_pairs(ptype, start_date, end_date):
    # pseudo code!
    while True:
        yield {
            'start_date': 'foo',
            'end_date': 'bar',
            'filters': ['']
        }

def query_ga(ptype, start_date=None, end_date=None):
    """queries GA per page-type, grouped by pagePath and date.
    each result will return 10k results max and there is no pagination.
    If every page of a given type is visited once a day for a year, then
    a single query with 10k results will service 27 pages.
    A safer number is 164, which means 6 queries per page-type per year.
    As we go further back in history the query will change as known epochs
    overlap. These overlaps will truncate the current period to the epoch
    boundaries. For example: if we chunk Jan-Dec 2017 into two-month chunks,
    Jan+Feb, Mar+Apr, etc, and an epoch where the 'news' page-type with
    pattern '/elife-news/.../' ends on Mar 20th and the current '/news/...'
    starts Mar 21st, then the two-month chunk spanning Mar+Apr 2017 will
    become Mar(1st)+Mar(20th) and Mar(21st)+Apr"""
    # until historical epochs are introduced, we just assume a single epoch
    # stretching back to the settings.INCEPTION_DATE

    # note: this is not how `elife.metrics.ga_metrics` works!
    # that module is doing a query for *every single day* since inception

    start_date = start_date or settings.INCEPTION
    end_date = end_date or date.today()
    table_id = settings.GA_TABLE_ID

    query_template = {
        'ids': table_id,
        'max_results': 10000, # 10k is the max GA will ever return
        'start_date': None, # set later
        'end_date': None, # set later
        'metrics': 'ga:sessions', # *not* pageviews
        'dimensions': 'ga:pagePath,ga:date',
        'sort': 'ga:pagePath,ga:date',
        'filters': None # set later
    }

    # pseudo code!
    for subqry in generate_date_pairs(ptype, start_date, end_date):
        ga_core.query_ga(defaultdict(query_template, subqry))


#
#
#

def daily_page_views(pobj):
    qobj = pobj.pagecount_set.all() # daily is the finest grain we have
    sums = qobj.aggregate(views_sum=Sum('views'))
    return sums['views_sum'] or 0, qobj

def monthly_page_views(pobj):
    qobj = pobj.pagecount_set \
        .annotate(month=TruncMonth('date')) \
        .values('month') \
        .annotate(views_sum=Sum('views')) \
        .values('month', 'views_sum')
    sums = pobj.pagecount_set.all().aggregate(views_sum=Sum('views'))
    return sums['views_sum'], qobj

#
#
#

def page_views(pid, ptype, period=DAY):
    ensure(is_pid(pid), "bad page identifier", ValueError)
    ensure(is_ptype(ptype), "bad page type", ValueError)
    ensure(is_period(period), "bad period", ValueError)
    try:
        pobj = models.Page.objects.get(identifier=pid, type=ptype)
        dispatch = {
            DAY: daily_page_views,
            MONTH: monthly_page_views
        }
        return dispatch[period](pobj)
    except models.Page.DoesNotExist:
        return None
