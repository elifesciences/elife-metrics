from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from article_metrics import api_v2_views as v2, api_v2_logic as v2_logic, utils
from . import models, logic
import logging

LOG = logging.getLogger(__name__)

# very similar to metrics.api_v2_views.metrics but:
# * no support for metric type (citations, downloads, etc)
# * relatively self-contained and separate from article metrics
# * msid is more strict than a pid
# * doesn't capture a 'month' period, relying instead on SQL

def serialise(total, sum_value, obj_list, period):
    def do_day(obj):
        return {
            'period': obj.date.strftime('%Y-%m-%d'),
            'value': obj.views
        }

    def do_month(obj):
        return {
            'period': obj['date_field'].strftime('%Y-%m'),
            'value': obj['views_sum']
        }

    do = do_day if period == logic.DAY else do_month

    return {
        'totalPeriods': total,
        'totalValue': sum_value,
        'periods': [do(obj) for obj in obj_list],
    }

@api_view(["GET"])
def metrics(request, ptype, pid=models.LANDING_PAGE):
    try:
        # /metrics/press-packages/12345/page-views?by=month
        kwargs = v2.request_args(request)
        get_object_or_404(models.Page, identifier=pid, type=ptype)
        sum_value, qobj = logic.page_views(pid, ptype, kwargs['period'])
        total_results, qpage = v2_logic.chop(qobj, **utils.exsubdict(kwargs, ['period']))
        payload = serialise(total_results, sum_value, qpage, kwargs['period'])
        ctype = 'application/vnd.elife.metric-time-period+json;version=1'
        return Response(payload, content_type=ctype)

    except Http404:
        raise # Page DNE, handled, ignore

    except AssertionError as err:
        raise ValidationError(err) # 400, client error

    except BaseException as err:
        LOG.exception("unhandled exception attempting to serve metrics: %s", err)
        raise # 500, server error
