from . import models
from metrics.utils import ensure
from django.db.models import Sum

DAY, MONTH = 'day', 'month'

def is_pid(pid):
    return isinstance(pid, str) and len(pid) < 256

def is_ptype(ptype):
    return isinstance(ptype, str) and len(ptype) < 256

def is_period(period):
    return period in [MONTH, DAY]

#
#
#

def daily_page_views(pobj):
    qobj = pobj.pagecount_set.all()
    sums = qobj.aggregate(views_sum=Sum('views'))
    return sums['views_sum'] or 0, qobj

def monthly_page_views(pobj):
    return 0, None

#
#
#

def page_views(pid, ptype, period=DAY):
    ensure(is_pid(pid), "bad page name", ValueError)
    ensure(is_ptype(ptype), "bad page type", ValueError)
    ensure(is_period(period), "bad period", ValueError)
    try:
        pobj = models.Page.objects.get(name=pid, type=ptype)
        dispatch = {
            DAY: daily_page_views,
            MONTH: monthly_page_views
        }
        return dispatch[period](pobj)
    except models.Page.DoesNotExist:
        return None
