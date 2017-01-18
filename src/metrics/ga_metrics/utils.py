import calendar
from datetime import datetime, timedelta
import logging

logging.basicConfig()
LOG = logging.getLogger(__name__)
LOG.level = logging.INFO

def ymd(dt):
    "returns a yyyy-mm-dd version of the given datetime object"
    return dt.strftime("%Y-%m-%d")

def month_min_max(dt):
    mmin, mmax = calendar.monthrange(dt.year, dt.month)
    return (datetime(year=dt.year, month=dt.month, day=1),
            datetime(year=dt.year, month=dt.month, day=mmax))

'''
# untested, unused
def is_month_range(dt1, dt2):
    """returns true if the first date represents the minium day for that
    year and month and the second date represents the maximum for that
    year and month"""
    mmin, _ = month_min_max(dt1)
    _, mmax = month_min_max(dt2)
    return dt1 == mmin and dt2 == mmax
'''

def dt_range_gen(from_date, to_date):
    """returns series of datetime objects starting at from_date
    and ending on to_date inclusive."""
    # unused, untested
    # if not to_date:
    #    to_date = from_date
    # if from_date > to_date:
    #    to_date, from_date = from_date, to_date
    diff = to_date - from_date
    for increment in range(0, diff.days + 1):
        dt = from_date + timedelta(days=increment)
        yield (dt, dt)  # daily

def dt_range(from_date, to_date):
    return list(dt_range_gen(from_date, to_date))

def dt_month_range_gen(from_date, to_date):
    # figure out a list of years and months the dates span
    ym = set()
    for dt1, dt2 in dt_range(from_date, to_date):
        ym.add((dt1.year, dt1.month))
    # for each pair, generate a month max,min datetime pair
    for year, month in sorted(ym):
        mmin, mmax = calendar.monthrange(year, month)
        yield (datetime(year=year, month=month, day=1),
               datetime(year=year, month=month, day=mmax))

def dt_month_range(from_date, to_date):
    return list(dt_month_range_gen(from_date, to_date))

def firstof(fn, x):
    for i in x:
        if fn(i):
            return i

def enplumpen(artid):
    "takes an article id like e01234 and returns a DOI like 10.7554/eLife.01234"
    return artid.replace('e', '10.7554/eLife.')

def deplumpen(artid):
    "takes an article id like eLife.01234 and returns a DOI like e01234"
    try:
        return "e" + artid.split('.')[1]
    except IndexError:
        # TODO: consider turning this into a hard failure
        LOG.error("unable to deplump %r", artid)
        return artid
    except:
        msg = "unhandled exception attempting to parse given value %r" % str(artid)
        LOG.error(msg)
        raise ValueError(msg)
