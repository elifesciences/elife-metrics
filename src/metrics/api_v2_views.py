from metrics import models
from django.shortcuts import get_object_or_404
import string
from django.conf import settings
from rest_framework.decorators import api_view
from et3.render import render_item
from et3.extract import path as p
from utils import isint, ensure, exsubdict, lmap, msid2doi
import api_v2_logic as logic
from rest_framework.response import Response

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
def article_metrics(request, id, metric):
    get_object_or_404(models.Article, doi=msid2doi(id))
    try:
        # /metrics/article/12345/downloads?by=month
        kwargs = request_args(request)
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
        return Response(serialize(total_results, sum_value, qpage, metric))

    except AssertionError as err:
        print err
        return 400 # client error
