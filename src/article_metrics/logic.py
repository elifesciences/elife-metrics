from functools import partial
from datetime import timedelta
from typing import Optional
from . import ga_metrics, models, utils, events
from django.conf import settings
from django.db import transaction
from .utils import first, create_or_update, ensure, splitfilter, comp, run, lfilter, datetime_now
import logging

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

def notify(obj, **kwargs):
    if not transaction.get_autocommit():
        # we're inside a managed transaction.
        # send the notification only after successful commit
        transaction.on_commit(lambda: events.notify(obj, **kwargs))
    else:
        events.notify(obj, **kwargs)

def recently_updated_citations(td):
    "all citations updated in the last given duration"
    since = utils.utcnow() - td
    return models.Citation.objects.filter(datetime_record_updated__gte=since).order_by('-article__doi')

def recently_updated_metrics(td):
    "all metrics updated in the last given duration"
    since = utils.utcnow() - td
    return models.Metric.objects.filter(datetime_record_updated__gte=since).order_by('-article__doi')

def recently_updated_article_notifications(**kwargs):
    "send notifications about all recently updated articles"
    td = timedelta(**kwargs)
    conn = events.event_bus_conn()
    for citation_obj in recently_updated_citations(td):
        notify(citation_obj, conn=conn)
    for metric_obj in recently_updated_metrics(td):
        notify(metric_obj, conn=conn)

#
#
#

def get_create_article(data):
    "single point for accessing/creating Articles. returns None on bad data"
    try:
        if 'doi' in data:
            msid = utils.doi2msid(data['doi'], allow_subresource=False)
            data['doi'] = utils.msid2doi(msid) # temporary, until doi field is replaced with msid field
        return first(create_or_update(models.Article, data, create=True, update=False))
    except AssertionError as err:
        # it shouldn't get to this point!
        LOG.warning("refusing to fetch/create bad article: %s" % err, extra={'article-data': data})

def _insert_row(data):
    "creates or updates a `models.Metric` in the database using `data`."
    article_obj = get_create_article({'doi': data['doi']})
    if not article_obj:
        LOG.warning("refusing to insert bad metric", extra={'row-data': data})
        return
    row = utils.exsubdict(data, ['doi'])
    row['article'] = article_obj
    key = utils.subdict(row, ['article', 'date', 'period', 'source'])
    return first(create_or_update(models.Metric, row, key, create=True, update=True, update_check=True))

@transaction.atomic
def insert_row(data):
    """inserts a metric dict into the database using a single transaction.
    DO NOT USE when inserting many objects. Use `insert_many_rows` or your performance will suffer greatly."""
    return _insert_row(data)

@transaction.atomic
def insert_many_rows(data_list):
    "inserts all items in given `data_list` using a single transaction."
    run(_insert_row, data_list)

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
    row = dict(list(zip(['period', 'date'], format_dt_pair(period))))
    row.update(views)
    return row

def import_ga_metrics(metrics_type='daily', from_date=None, to_date=None, use_cached=True, use_only_cached=False):
    "import metrics from GA between the two given dates or from the inception date in `settings.py`"
    ensure(metrics_type in ['daily', 'monthly'], 'metrics type must be either "daily" or "monthly"')

    table_id = 'ga:%s' % settings.GA3_TABLE_ID
    the_beginning = ga_metrics.core.VIEWS_INCEPTION
    yesterday = datetime_now() - timedelta(days=1)

    if not from_date:
        from_date = the_beginning

    if not to_date:
        # don't import today's partial results. they're available but lets wait until tomorrow
        to_date = yesterday

    f = {
        'daily': ga_metrics.core.daily_metrics_between,
        'monthly': ga_metrics.core.monthly_metrics_between,
    }
    results = f[metrics_type](table_id, from_date, to_date, use_cached, use_only_cached)

    for period, metrics in results.items():
        views, downloads = metrics['views'], metrics['downloads']
        # there is often a disjoint between articles that have been viewed and those downloaded within a period
        # what we do is create a record for *all* articles seen, even if their views or downloads may not exist
        doi_list = set(views.keys()).union(list(downloads.keys()))
        row_list = [create_row(doi, period, views.get(doi), downloads.get(doi)) for doi in doi_list]
        # insert rows in batches of 1000
        run(insert_many_rows, utils.partition(row_list, 1000))

#
# citations
#

def insert_citation(data, aid='doi'):
    article_obj = get_create_article({aid: data[aid]})
    if not article_obj:
        LOG.warning("refusing to insert bad citation", extra={'citation-data': data})
        return
    row = utils.exsubdict(data, [aid])
    row['article'] = article_obj
    key = utils.subdict(row, ['article', 'source'])
    return create_or_update(models.Citation, row, key, create=True, update=True, update_check=True)

def countable(triple):
    "if the citation has been created or modified, return the object"
    if triple:
        citation, created, updated = triple
        if created or updated:
            return citation

def import_scopus_citations():
    from .scopus.citations import all_todays_entries
    results = all_todays_entries()
    good_eggs, bad_eggs = splitfilter(lambda e: 'bad' not in e, results)
    LOG.warning("refusing to insert %s bad entries", len(bad_eggs), extra={'bad-entries': bad_eggs})
    run(comp(insert_citation, countable), good_eggs)

def import_pmc_citations():
    from .pm.citations import citations_for_all_articles
    results = citations_for_all_articles()
    run(comp(partial(insert_citation, aid='pmcid'), countable), results)

def import_crossref_citations(msid: Optional[str] = None):
    from .crossref.citations import citations_for_articles
    results = citations_for_articles(msid=msid)
    run(comp(insert_citation, countable), lfilter(None, results))
