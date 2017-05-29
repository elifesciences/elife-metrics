from functools import partial
from datetime import datetime, timedelta
import ga_metrics
from ga_metrics import bulk
from django.conf import settings
import models
from django.db import transaction
#from django.db.models import Q
import utils
from utils import first, create_or_update, ensure, splitfilter, comp
import logging
import events

LOG = logging.getLogger(__name__)

def format_dt_pair(dt_pair):
    """the database expects values in yyyy-mm or yyyy-mm-dd format.
    this function takes a pair of datetime objects and returns a pair of
    `(type, datestring)`, for example `('day', '2015-01-31')` for daily
    of `('month', '2015-01')` for monthly"""
    from_date, to_date = dt_pair
    if from_date == to_date:
        # daily, looks like 2015-01-01, 2015-01-01
        return models.DAY, from_date
    if from_date[-2:] == '01' and to_date[-2:] in ['31', '30', '29', '28']:
        # monthly, looks 2015-01-01, 2015-01-31
        return models.MONTH, from_date[:7]
    raise ValueError("given dtpair %r but it doesn't look like a daily or monthly result!" % str(dt_pair))

#
#
#

def notify(obj):
    if not transaction.get_autocommit():
        # we're inside a managed transaction.
        # send the notification only after successful commit
        transaction.on_commit(partial(events.notify, obj))
    else:
        events.notify(obj)

'''
def recently_updated_articles():
    "all articles whose associated metrics/citations have been updated in the last hour"
    since = utils.utcnow() - timedelta(hours=2)
    recent_citations = Q(citation__datetime_record_updated__gte=since)
    recent_views_downloads = Q(metric__datetime_record_updated__gte=since)
    return models.Article.objects.filter(recent_citations | recent_views_downloads).distinct()
'''

def recently_updated_citations(td):
    "all articles whose associated metrics/citations have been updated in the last hour"
    since = utils.utcnow() - td
    return models.Citation.objects.filter(datetime_record_updated__gte=since).order_by('-article__doi')

def recently_updated_metrics(td):
    since = utils.utcnow() - td
    return models.Metric.objects.filter(datetime_record_updated__gte=since).order_by('-article__doi')

def recently_updated_article_notifications(**kwargs):
    "send notifications about all articles recently updated"
    td = timedelta(**kwargs)
    map(notify, recently_updated_citations(td))
    map(notify, recently_updated_metrics(td))

#
#
#

def create_row(doi, period, views, downloads):
    "wrangles the data into a format suitable for `insert_row`"
    views = views or {
        'full': 0,
        'abstract': 0,
        'digest': 0,
    }
    views['pdf'] = downloads or 0
    views['doi'] = doi
    views['source'] = models.GA
    row = dict(zip(['period', 'date'], format_dt_pair(period)))
    row.update(views)
    return row

def _insert_row(data):
    article_obj = first(create_or_update(models.Article, {'doi': data['doi']}, ['doi'], create=True, update=False))
    row = utils.exsubdict(data, ['doi'])
    row['article'] = article_obj
    key = utils.subdict(row, ['article', 'date', 'period', 'source'])
    return first(create_or_update(models.Metric, row, key, create=True, update=True, update_check=True))

@transaction.atomic
def insert_row(data):
    """inserts a metric into the database within a transaction. DO NOT USE if you are inserting many
    metrics. use `insert_many_rows` or your performance will suffer greatly"""
    return _insert_row(data)

@transaction.atomic
def insert_many_rows(data_list):
    return map(_insert_row, data_list)

def import_ga_metrics(metrics_type='daily', from_date=None, to_date=None, use_cached=True, use_only_cached=False):
    "import metrics from GA between the two given dates or from inception"
    ensure(metrics_type in ['daily', 'monthly'], 'metrics type must be either "daily" or "monthly"')

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

    for period, metrics in results.items():
        views, downloads = metrics['views'], metrics['downloads']
        # there is often a disjoint between articles that have been viewed and those downloaded within a period
        # what we do is create a record for *all* articles seen, even if their views or downloads may not exist
        doi_list = set(views.keys()).union(downloads.keys())
        row_list = [create_row(doi, period, views.get(doi), downloads.get(doi)) for doi in doi_list]
        # insert rows in batches of 1000
        map(insert_many_rows, utils.partition(row_list, 1000))

#
# citations
#

def insert_citation(data, aid='doi'):
    # ll: ... = first(create_or_update(models.Article, {'doi': data['doi']}, ['doi'], create=True, update=False))
    article_obj = first(create_or_update(models.Article, {aid: data[aid]}, [aid], create=True, update=False))
    row = utils.exsubdict(data, [aid])
    row['article'] = article_obj
    key = utils.subdict(row, ['article', 'source'])
    return create_or_update(models.Citation, row, key, create=True, update=True, update_check=True)

def countable(triple):
    "if the citation has been created or modified, return the object"
    citation, created, updated = triple
    if created or updated:
        return citation

def import_scopus_citations():
    from scopus.citations import all_todays_entries
    results = all_todays_entries()
    good_eggs, bad_eggs = splitfilter(lambda e: 'bad' not in e, results)
    LOG.error("refusing to insert bad entries: %s", bad_eggs)
    return map(comp(insert_citation, countable), good_eggs)

def import_pmc_citations():
    from pm.citations import citations_for_all_articles
    results = citations_for_all_articles()
    return map(comp(partial(insert_citation, aid='pmcid'), countable), results)

def import_crossref_citations():
    from crossref.citations import citations_for_all_articles
    results = citations_for_all_articles()
    return map(comp(insert_citation, countable), filter(None, results))
