import models
import utils
from utils import ensure, rest, lmap
from django.db.models import Sum, F, Max

def chop(q, page, per_page, order):
    """orders and chops a query into pages, returning the total of the original query and a query object"""
    total = q.count()

    order_by_idx = {
        models.Metric: 'date',
        models.Citation: 'num',
    }
    order_by = order_by_idx[q.model]

    # switch directions if descending (default ASC)
    if order is 'DESC':
        order_by = '-' + order_by

    q = q.order_by(order_by)

    # a per-page = 0 means 'all results'
    if per_page > 0:
        start = (page - 1) * per_page
        end = start + per_page
        q = q[start:end]

    return total, q

def pad_citations(serialized_citation_response):
    cr = serialized_citation_response
    known_sources = dict(models.source_choices()).keys()
    missing_sources = set(known_sources) - set([cite['service'] for cite in cr])

    def pad(source):
        return {
            'service': source,
            'uri': '',
            'citations': 0
        }
    return cr + lmap(pad, missing_sources)

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
        views=Sum(F('full') + F('abstract')),
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
