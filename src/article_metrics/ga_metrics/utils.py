import calendar
from datetime import datetime, timedelta
import logging
from article_metrics.utils import ensure, isint, msid2doi

LOG = logging.getLogger(__name__)

def norm_table_id(table_id):
    if str(table_id).startswith('ga:'):
        return table_id
    return "ga:%s" % str(int(table_id))

def ymd(dt):
    "returns a yyyy-mm-dd version of the given datetime object"
    if isinstance(dt, str):
        return dt
    return dt.strftime("%Y-%m-%d")

def month_min_max(dt):
    mmin, mmax = calendar.monthrange(dt.year, dt.month)
    return (datetime(year=dt.year, month=dt.month, day=1),
            datetime(year=dt.year, month=dt.month, day=mmax))

def dt_range_gen(from_date, to_date):
    """returns series of datetime objects starting at from_date
    and ending on to_date inclusive."""
    diff = to_date - from_date
    for increment in range(0, diff.days + 1):
        dt = from_date + timedelta(days=increment)
        yield (dt, dt)  # daily

def dt_range(from_date, to_date):
    return list(dt_range_gen(from_date, to_date))

def dt_month_range_gen(from_date, to_date, preserve_caps=False):
    from_date, to_date = d2dt(from_date), d2dt(to_date)

    # figure out a list of years and months the dates span
    ym_range = set()
    for dt1, dt2 in dt_range(from_date, to_date):
        ym_range.add((dt1.year, dt1.month))
    ym_range = sorted(ym_range)

    # trim the ends of the range we'll generate. we'll do those manually
    if preserve_caps:
        if len(ym_range) == 1:
            # very edge case:
            # two dates for a month range, both in same year and month, preserve_caps=True
            yield (from_date, to_date)
            return

        # [1, 2, 3][1:-1] => [2]
        # [1, 2][1:-1] => [] (no range will be generated)
        ym_range = ym_range[1:-1]

        # return first pair of `from_date` + `from_date` maximum
        yield (from_date, month_min_max(from_date)[1])

    # for each pair, generate a month max,min datetime pair
    for year, month in ym_range:
        mmin, mmax = calendar.monthrange(year, month)
        yield (datetime(year=year, month=month, day=1),
               datetime(year=year, month=month, day=mmax))

    if preserve_caps:
        # return the final pair of `to_date` minimum + `to_date`
        yield (month_min_max(to_date)[0], to_date)

def dt_month_range(from_date, to_date, preserve_caps=False):
    return list(dt_month_range_gen(from_date, to_date, preserve_caps))

def firstof(fn, x):
    for i in x:
        if fn(i):
            return i

def enplumpen(artid):
    "takes an article id like e01234 and returns a DOI like 10.7554/eLife.01234"
    if isint(artid):
        return msid2doi(artid)
    ensure(artid[0] == 'e', 'cannot convert article id %s to doi' % artid)
    return artid.replace('e', '10.7554/eLife.')

def deplumpen(artid):
    "takes an article id like eLife.01234 and returns a DOI like e01234"
    try:
        return "e" + artid.split('.')[1]
    except IndexError:
        # TODO: consider turning this into a hard failure
        LOG.error("unable to deplump %r", artid)
        return artid
    except BaseException:
        msg = "unhandled exception attempting to parse given value %r" % str(artid)
        LOG.error(msg)
        raise ValueError(msg)

def d2dt(d):
    if isinstance(d, datetime):
        return d
    return datetime(year=d.year, month=d.month, day=d.day, hour=0, minute=0, second=0)
