from metrics import models
from django.shortcuts import get_object_or_404
import string
from django.conf import settings
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import StaticHTMLRenderer
from et3.render import render_item
from et3.extract import path as p
from utils import isint, ensure, exsubdict, lmap, msid2doi
import api_v2_logic as logic
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
            ensure(val in lst, "value %r is not in %r" % (val, lst))
            return val
        return fn

    desc = {
        'page': [p('page', opts['page_num']), ispositiveint],
        'per_page': [p('per-page', opts['per_page']), ispositiveint, inrange(opts['min_per_page'], opts['max_per_page'])],
        'order': [p('order', opts['order_direction']), string.upper, isin(['ASC', 'DESC'])],

        'period': [p('by', 'day'), string.lower, isin(['day', 'month'])],
    }
    return render_item(desc, request.GET)

#
#
#

def serialize_citations(obj_list):
    def do(obj):
        return {
            'service': obj.source,
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
@renderer_classes((StaticHTMLRenderer,))
def ping(request):
    return Response('pong', content_type='text/plain; charset=UTF-8', headers={'Cache-Control': 'must-revalidate, no-cache, no-store, private'})

@api_view(['GET'])
def article_metrics(request, id, metric):
    try:
        # /metrics/article/12345/downloads?by=month
        kwargs = request_args(request) # parse args first ...
        get_object_or_404(models.Article, doi=msid2doi(id)) # ... then a db lookup
        idx = {
            'citations': logic.article_citations,
            'downloads': logic.article_downloads,
            'page-views': logic.article_views,
        }
        # fetch our results
        sum_value, qobj = idx[metric](id, kwargs['period'])
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

    except AssertionError as err:
        raise ValidationError(err) # 400, client error

    except Exception as err:
        LOG.exception("unhandled exception attempting to serve article metrics: %s", err)
        raise # 500, server error
