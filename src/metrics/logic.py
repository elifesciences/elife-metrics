from functools import partial
from datetime import datetime, timedelta
import ga_metrics
from ga_metrics import bulk
from django.conf import settings
import models
from django.db import transaction
import utils
from utils import first, create_or_update, ensure, splitfilter, comp
from django import db
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

def insert_row(data):
    article_obj = first(create_or_update(models.Article, {'doi': data['doi']}, ['doi'], create=True, update=False))
    row = utils.exsubdict(data, ['doi'])
    row['article'] = article_obj
    key = utils.subdict(row, ['article', 'date', 'period', 'source'])
    return first(create_or_update(models.Metric, row, key, create=True, update=True, update_check=True))

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
    # TODO: does this even work???
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
# citations
#

def insert_citation(data, aid='doi'):
    # ll: ... = first(create_or_update(models.Article, {'doi': data['doi']}, ['doi'], create=True, update=False))
    article_obj = first(create_or_update(models.Article, {aid: data[aid]}, [aid], create=True, update=False))
    row = utils.exsubdict(data, [aid])
    row['article'] = article_obj
    key = utils.subdict(row, ['article', 'source'])
    return create_or_update(models.Citation, row, key, create=True, update=True, update_check=True)

def countable(citation, created, updated):
    "if the citation has been created or modified, return the object"
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

#
#
#

def notify(obj_list):
    "given a list of Citation or Metric objects, sends 'updated' events for each one"
    # the output from the `import_*_citations` may contain None values if
    # a citation wasn't created or updated.
    lst = filter(None, obj_list)
    # send events for all those that have changed
    return len(map(events.notify, lst))
