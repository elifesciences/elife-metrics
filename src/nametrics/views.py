from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from metrics import api_v2_views as v2, api_v2_logic as v2_logic, utils
from . import models
import logging

LOG = logging.getLogger(__name__)

# very similar to metrics.api_v2_views.metrics but:
# * no support for metric type (citations, downloads, etc)
# * relatively self-contained and separate from article metrics
# * msid is more strict than a pid

@api_view(["GET"])
def metrics(request, ptype, pid):
    try:
        # /metrics/press-packages/12345/page-views?by=month
        kwargs = v2.request_args(request)
        get_object_or_404(models.Page, name=pid, type=ptype)
        sum_value, qobj = v2_logic.views(pid, ptype, kwargs['period'])
        total_results, qpage = v2_logic.chop(qobj, **utils.exsubdict(kwargs, ['period']))
        payload = v2.serialize(total_results, sum_value, qpage, 'page-views')
        ctype = 'application/vnd.elife.metric-time-period+json;version=1'
        return Response(payload, content_type=ctype)

    except Http404:
        raise # Page DNE, handled, ignore

    except AssertionError as err:
        raise ValidationError(err) # 400, client error

    except BaseException as err:
        LOG.exception("unhandled exception attempting to serve metrics: %s", err)
        raise # 500, server error
