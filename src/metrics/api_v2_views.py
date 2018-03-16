from metrics import models
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.conf import settings
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import StaticHTMLRenderer
from et3.render import render_item
from et3.extract import path as p
from et3.utils import uppercase, lowercase
from .utils import isint, ensure, exsubdict, lmap, msid2doi
from . import api_v2_logic as logic
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

import logging

LOG = logging.getLogger(__name__)

def request_args(request, **overrides):
    opts = {}
    opts.update(settings.API_OPTS)
    opts.update(overrides)

    def ispositiveint(v):
        ensure(isint(v) and int(v) > 0, "expecting positive integer, got: %s" % v)
        return int(v)

    def inrange(minpp, maxpp):
        def fn(v):
            ensure(v >= minpp and v <= maxpp, "value must be between %s and %s" % (minpp, maxpp))
            return v
        return fn

    def isin(lst):
        def fn(val):
            ensure(val in lst, "value is not in %r" % (lst,))
            return val
        return fn

    desc = {
        'page': [p('page', opts['page_num']), ispositiveint],
        'per_page': [p('per-page', opts['per_page']), ispositiveint, inrange(opts['min_per_page'], opts['max_per_page'])],
        'order': [p('order', opts['order_direction']), uppercase, isin(['ASC', 'DESC'])],

        'period': [p('by', 'day'), lowercase, isin(['day', 'month'])],
    }
    return render_item(desc, request.GET)

#
#
#

def serialize_citations(obj_list):
    def do(obj):
        return {
            'service': obj.source_label(),
            'uri': obj.source_id,
            'citations': obj.num
        }
    return lmap(do, obj_list)

def serialize_views_downloads(metric, total, sum_value, obj_list):
    attr = 'views' if metric == 'page-views' else 'downloads'

    def do(obj):
        return {
            'period': obj.date,
            'value': getattr(obj, attr)
        }
    return {
        'totalPeriods': total,
        'totalValue': sum_value,
        'periods': lmap(do, obj_list),
    }

def serialize(total_results, sum_value, obj_list, metric):
    if metric == 'citations':
        return serialize_citations(obj_list)
    return serialize_views_downloads(metric, total_results, sum_value, obj_list)

#
#
#

@api_view(['GET'])
def article_metrics(request, msid, metric):
    try:
        # /metrics/article/12345/downloads?by=month
        kwargs = request_args(request) # parse args first ...
        get_object_or_404(models.Article, doi=msid2doi(msid)) # ... then a db lookup
        idx = {
            'citations': logic.article_citations,
            'downloads': logic.article_downloads,
            'page-views': logic.article_views,
        }
        # fetch our results
        sum_value, qobj = idx[metric](msid, kwargs['period'])
        # paginate
        total_results, qpage = logic.chop(qobj, **exsubdict(kwargs, ['period']))
        # serialize
        payload = serialize(total_results, sum_value, qpage, metric)

        # citations have to return zeroes for any missing sources
        payload = logic.pad_citations(payload) if metric == 'citations' else payload

        # respond
        ctype_idx = {
            'citations': 'application/vnd.elife.metric-citations+json;version=1',
            'downloads': 'application/vnd.elife.metric-time-period+json;version=1',
            'page-views': 'application/vnd.elife.metric-time-period+json;version=1',
        }
        return Response(payload, content_type=ctype_idx[metric])

    except Http404:
        raise # Article DNE, handled, ignore

    except AssertionError as err:
        raise ValidationError(err) # 400, client error

    except BaseException as err:
        LOG.exception("unhandled exception attempting to serve article metrics: %s", err)
        raise # 500, server error

#
#
#

@api_view(['GET'])
@renderer_classes((StaticHTMLRenderer,))
def ping(request):
    "Returns a constant response for monitoring. Never to be cached."
    return Response('pong', content_type='text/plain; charset=UTF-8', headers={'Cache-Control': 'must-revalidate, no-cache, no-store, private'})

#
#
#

@api_view(['GET'])
def summary(request, msid=None):
    "returns the final totals for all articles with no finer grained information"
    try:
        kwargs = request_args(request)
        # TODO: we have a '10.7554/eLife.00000' in models.Article that needs deleting
        #qobj = models.Article.objects.all()
        qobj = models.Article.objects.all() \
            .exclude(doi='10.7554/eLife.00000')

        if msid:
            qobj = qobj.filter(doi=msid2doi(msid))

        total_results, qpage = logic.chop(qobj, **exsubdict(kwargs, ['period']))

        if msid and total_results == 0:
            raise Http404("summary for article does not exist")

        payload = lmap(logic.summary_by_obj, qpage)

        payload = {
            'total': total_results,
            'items': payload
        }
        return Response(payload, content_type="application/json")

    except AssertionError as err:
        raise ValidationError(err) # 400, client error

    except Exception as err:
        LOG.exception("unhandled exception attempting to serve article metrics: %s", err)
        raise # 500, server error
