import models
import utils
from utils import first, rest, lmap, ensure
from django.db.models import Q, Sum, F, Max

def chop(q, page, per_page, order):
    """orders and chops a query into pages, returning the total of the original query and a query object"""
    total = q.count()

    order_by_idx = {
        models.Metric: 'date',
        models.Citation: 'num',
    }
    order_by = order_by_idx[q.model]

    # switch directions if descending (default ASC)
    if order == 'DESC':
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
    # TODO: bug here. pads will have the order of
    # models.SOURCE_LABELS (alphabetical, asc) and not what the user specified
    missing_sources = set(models.SOURCE_LABELS) - set([cite['service'] for cite in cr])

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

def article_citations(msid, period=None, source=None):
    # all citations belonging to given article
    # where number of citations > 0
    qobj = models.Citation.objects \
        .filter(article__doi__iexact=utils.msid2doi(msid)) \
        .filter(num__gt=0)
    # NICETOHAVE: not supported, but absolutely do-able
    # if source:
    #    qobj = qobj.filter(source=source)
    sums = qobj.aggregate(Max('num'))
    return sums['num__max'] or 0, qobj

# probably very cacheable
def hw_terminator(msid, period):
    "returns the yyyy-mm-dd or yyyy-mm of when hw metrics stop for this article"
    # value will be variously in the range from 2015-10-14 to 2016-02-08 or None
    qobj = models.Metric.objects \
        .filter(article__doi__iexact=utils.msid2doi(msid)) \
        .filter(period=period) \
        .filter(source=models.HW) \
        .order_by('-date')
    return getattr(first(qobj), 'date', None)

# temporary.
def gabeforeafter(msid, period, term):
    #term = hw_terminator(msid)
    if not term:
        xxx = {'views': None, 'dls': None}
        return xxx, xxx

    qobj = models.Metric.objects \
      .filter(article__doi__iexact=utils.msid2doi(msid)) \
      .filter(period=period) \
      .filter(source=models.GA)

    before = qobj.filter(date__lte=term)
    sums = before.aggregate(
        views=Sum(F('full') + F('abstract') + F('digest')),
        downloads=Sum('pdf'))

    before = {
        'views': sums['views'] or 0,
        'dls': sums['downloads'] or 0
    }

    after = qobj.exclude(date__lte=term)
    sums = after.aggregate(
        views=Sum(F('full') + F('abstract') + F('digest')),
        downloads=Sum('pdf'))

    after = {
        'views': sums['views'] or 0,
        'dls': sums['downloads'] or 0
    }

    return before, after


def prefer_hw(qobj, msid, period, source):
    """
    elife-metrics has two sources of Metric objects, 'hw' and 'ga'.
    the 'hw' data is suspect, we can't interrogate it, don't know how it was
    counted or transformed, is wildly different to 'ga' data and is no longer captured.

    however, the 'hw' source of data goes back farther in time and it's very
    large numbers are pleasing to authors (sound familiar?)

    this function ensures a single query object is still available to be
    ordered and chopped up while doing some gymnastics to ensure no overlap
    occurs between the 'hw' and 'ga' sources, with the 'hw' source preferred.

    the logic below is very straightforward.

    """
    if source:
        # a specific source has been requested, no hacking required
        return qobj

    if msid > 14383:
        # 14383 was the last article to have hw stats
        return qobj

    hwt = hw_terminator(msid, period)
    if not hwt:
        # article has no hw metrics
        return qobj

    # exclude all GA data before HW data
    return qobj.exclude(Q(source=models.GA) & Q(date__lte=hwt))

def article_stats(msid, period, source, prefer_hw_metrics=True):
    ensure(period in [models.MONTH, models.DAY], "unknown period %r" % period)
    qobj = models.Metric.objects \
        .filter(article__doi__iexact=utils.msid2doi(msid)) \
        .filter(period=period)

    if source:
        ensure(source in models.KNOWN_METRIC_SOURCES, "unknown source %r" % source)
        qobj = qobj.filter(source=source)

    if prefer_hw_metrics:
        # exclude overlapping GA results
        qobj = prefer_hw(qobj, msid, period, source)

    sums = qobj.aggregate(
        views=Sum(F('full') + F('abstract') + F('digest')),
        downloads=Sum('pdf'))
    return sums['views'] or 0, sums['downloads'] or 0, qobj

def article_downloads(msid, period, source):
    # convenience
    total_downloads, qobj = rest(article_stats(msid, period, source))
    return total_downloads, qobj

def article_views(msid, period, source):
    # convenience
    total_views, _, qobj = article_stats(msid, period, source)
    return total_views, qobj
