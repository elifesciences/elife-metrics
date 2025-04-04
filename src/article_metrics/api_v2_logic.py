import cachetools
import os
from collections import OrderedDict

import requests
from . import models
from . import utils
from .utils import ensure, rest, lmap
from kids.cache import cache
from django.db.models import Sum, F, Max
import logging
import metrics.models
import article_metrics.crossref.citations as crossref
from django.db import connection
from django.conf import settings
from psycopg2.extensions import AsIs

LOG = logging.getLogger(__name__)

def chop(q, page, per_page, order):
    """orders and chops a query into pages, returning the total of the original query and a query object"""
    total = q.count()

    order_by_idx = {
        models.Article: 'doi',
        models.Metric: 'date',
        models.Citation: 'num',
        metrics.models.PageCount: 'date_field',
    }
    order_by = order_by_idx[q.model]

    # switch directions if descending (default ASC)
    if order == 'DESC':
        order_by = '-' + order_by

    more_sorting = {
        models.Citation: lambda _: (order_by, 'source'),
    }
    default = lambda _: (order_by,)
    order_by = more_sorting.get(q.model, default)(order_by)

    q = q.order_by(*order_by)

    # a per-page = 0 means 'all results'
    if per_page > 0:
        start = (page - 1) * per_page
        end = start + per_page
        q = q[start:end]

    return total, q

def pad_citations(serialized_citation_response):
    cr = serialized_citation_response
    missing_sources = set(models.SOURCE_LABELS) - set([cite['service'] for cite in cr])
    if not missing_sources:
        return cr
    # WARN: thorny logic here
    # results are sorted by number, but when there are no results for a service we pad
    # with a zero result. when multiple citations have the same number, results are then
    # sorted alphabetically by source (service).

    def pad(source):
        return {
            'service': source,
            'uri': '',
            'citations': 0
        }
    pads = lmap(pad, missing_sources)
    pads = sorted(pads, key=lambda r: r['service'])
    return cr + pads

#
#
#

def article_citations(msid, period=None):
    # all citations belonging to given article
    # where number of citations > 0
    qobj = models.Citation.objects \
        .filter(article__doi__iexact=utils.msid2doi(msid)) \
        .filter(num__gt=0)
    sums = qobj.aggregate(Max('num'))
    return sums['num__max'] or 0, qobj

def article_stats(msid, period):
    ensure(period in [models.MONTH, models.DAY], "unknown period %r" % period)
    qobj = models.Metric.objects \
        .filter(article__doi__iexact=utils.msid2doi(msid)) \
        .filter(source=models.GA) \
        .filter(period=period)
    sums = qobj.aggregate(
        views=Sum(F('full') + F('abstract') + F('digest')),
        downloads=Sum('pdf'))
    return sums['views'] or 0, sums['downloads'] or 0, qobj

def article_downloads(msid, period):
    # convenience
    total_downloads, qobj = rest(article_stats(msid, period))
    return total_downloads, qobj

def article_views(msid, period):
    # convenience
    total_views, _, qobj = article_stats(msid, period)
    return total_views, qobj

#
#
#

def summary_by_msid(msid):
    views, downloads, _ = article_stats(msid, models.DAY)
    row = OrderedDict([
        ('id', msid),
        ('views', views),
        ('downloads', downloads),
        (models.CROSSREF, 0),
        (models.PUBMED, 0),
        (models.SCOPUS, 0)
    ])
    _, qobj = article_citations(msid)
    row.update(dict(lmap(lambda obj: (obj.source, obj.num), qobj.order_by('source'))))
    return row

def summary_by_obj(artobj):
    try:
        return summary_by_msid(utils.doi2msid(artobj.doi))
    except AssertionError:
        LOG.warning("bad data, skipping article: %s", artobj)


#
#
#


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def coerce_summary_row(row):
    "post-processing of rows from `summary`, because we can't do everything in SQL"
    try:
        row['id'] = utils.doi2msid(row['id'])
        return row
    except Exception:
        LOG.warning("bad data, skipping article: %s", row)

SUMMARY_SQL_ALL = open(os.path.join(settings.SQL_PATH, 'metrics-summary.sql'), 'r').read()
TWO_MIN_CACHE = cachetools.TTLCache(maxsize=1, ttl=120 if not settings.TESTING else 0)

@cache(use=TWO_MIN_CACHE)
def _summary(order):
    """an optimised query for returning article metric summaries.
    execution time is the same for all results or just one, so pagination is skipped."""
    with connection.cursor() as cursor:
        cursor.execute(SUMMARY_SQL_ALL, [AsIs(order)])
        rows = dictfetchall(cursor)
    return list(filter(None, map(coerce_summary_row, rows)))

def summary(page, per_page, order):
    """an optimised query for returning article metric summaries.
    execution time is the same for all results or just one, so pagination uses list slices."""
    rows = _summary(order) # pylint: disable=E1111
    # ?per-page=100&page=1 = 0:100
    # ?per-page=100&page=2 = 100:200
    start_pos = per_page * (page - 1) # slices are 0-based
    offset = start_pos + per_page
    return len(rows), rows[start_pos:offset]


@cache(use=TWO_MIN_CACHE)
def citations_by_version(msid, version):
    doi = f"{utils.msid2doi(msid)}.{version}"
    with requests.Session() as requests_session:
        crossref_citations = crossref.parse(crossref.fetch(doi, requests_session=requests_session), doi)

    if not crossref_citations:
        return None

    # citations have to return zeroes for any missing sources
    return [
        {
            'service': models.CROSSREF_LABEL,
            'uri': crossref_citations['source_id'],
            'citations': crossref_citations['num']
        },
        {
            'service': models.PUBMED_LABEL,
            'uri': '',
            'citations': 0
        },
        {
            'service': models.SCOPUS_LABEL,
            'uri': '',
            'citations': 0
        }
    ]
