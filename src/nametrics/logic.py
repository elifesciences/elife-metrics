from . import models
from metrics.utils import ensure, lmap, create_or_update, first, merge, tod, ymd
from metrics.ga_metrics import core as ga_core, utils as ga_utils
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.conf import settings
from datetime import date, datetime
from django.db import transaction
import json
import os
from kids.cache import cache as cached
from functools import partial
import logging
from urllib.parse import urlparse

LOG = logging.getLogger(__name__)

DAY, MONTH = 'day', 'month'

def is_pid(pid):
    return isinstance(pid, str) and len(pid) < 256

def is_ptype(ptype):
    return isinstance(ptype, str) and len(ptype) < 256

def is_period(period):
    return period in [MONTH, DAY]

def is_date(dt):
    return isinstance(dt, date)

#
# utils
#

def _str2dt(string):
    return datetime.strptime(string, "%Y%m%d")

def mkidx(rows, keyfn):
    idx = {}
    for row in rows:
        key = keyfn(row)
        group = idx.get(key, [])
        group.append(row)
        idx[key] = group
    return idx

def get(k, d=None):
    "`get('key', {}) => `{}.get('key')` but also `get('key')({})` => `{}.get('key')`"
    if not d:
        return lambda d: get(k, d)
    return d.get(k)

#
#
#

def process_path(prefix, path):
    path = urlparse(path).path
    # we could just dispense with the prefix and discard the first segment ...
    prefix_len = len(prefix)
    path = path[prefix_len:].strip().strip('/') # /events/foobar => foobar
    path = path.split('/', 1)[0] # foobar/the-baz-in-bar-fooed-at-the-star => foobar
    return path

def process_object(prefix, rows):
    def _process(row):
        path, datestr, count = row
        path = process_path(prefix, path)
        return {
            'views': int(count),
            'date': _str2dt(datestr),
            'identifier': path,
        }
    return lmap(_process, rows)

#
#
#

def asmaps(rows):
    "convenience, converts a list of rows into dicts"
    return [dict(zip(['identifier', 'date', 'views'], row)) for row in rows]

def aggregate(normalised_rows):
    "counts up the number of times each page was visited"
    # group together the rows by id and date.
    # it's possible after normalisation for two paths to exist on same date
    idx = mkidx(normalised_rows, lambda row: (row['identifier'], row['date']))
    # return single record for each group, replacing 'views' with the sum of views in the group
    rows = [(grp[0]['identifier'], grp[0]['date'], sum(map(get('views'), grp))) for grp in idx.values()]
    rows = asmaps(rows)

    # sort rows by date and then path
    # not necessary, but makes output nicer
    rows = sorted(rows, key=lambda r: ymd(r['date']) + r['identifier'], reverse=True) # DESC

    return rows

#
#
#

def process_response(ptype, frame, response):
    processor_map = {
        # 'blog-article': process_blog,
        # 'event': process_event,
        # 'interview': process_interview,
        # 'labs-post': process_labs,
        # 'press-package': process_presspackages,
    }
    processor = processor_map.get(ptype)
    if not processor:
        ensure('prefix' in frame, "no processor for %r and no `prefix` key found in history - cannot process results" % ptype)
        processor = partial(process_object, frame['prefix'])
    normalised = processor(response.get('rows', []))
    return normalised

def query_ga(ptype, query):
    sd, ed = query['start_date'], query['end_date']
    LOG.info("querying GA for %ss between %s and %s" % (ptype, sd.date(), ed.date()))
    dump_path = ga_core.output_path(ptype, sd, ed)
    if os.path.exists(dump_path):
        # temporary caching while I debug
        LOG.debug("(cache hit)")
        return json.load(open(dump_path, 'r'))
    raw_response = ga_core.query_ga(query) # potentially 10k worth, but in actuality ...
    ga_core.write_results(raw_response, dump_path)
    return raw_response

@cached
def load_ptype_history(ptype):
    ptype_history = json.load(open(settings.GA_PTYPE_HISTORY_PATH, 'r'))
    ensure(ptype in ptype_history, "no historical data found: %s" % ptype, ValueError)
    return ptype_history[ptype]

def generic_ga_filter(prefix):
    "returns a generic GA pattern that handles `/prefix` and `/prefix/what/ever` patterns"
    return "ga:pagePath=~^{prefix}$,ga:pagePath=~^{prefix}/.*$".format(prefix=prefix)

def build_ga_query(ptype, start_date=None, end_date=None, history=None):
    """queries GA per page-type, grouped by pagePath and date.
    each result will return 10k results max and there is no pagination.
    If every page of a given type is visited once a day for a year, then
    a single query with 10k results will service 27 pages.
    A safer number is 164, which means 6 queries per page-type per year.

    As we go further back in history the query will change as known epochs
    overlap. These overlaps will truncate the current period to the epoch
    boundaries. For example: if we chunk Jan-Dec 2017 into two-month chunks,
    Jan+Feb, Mar+Apr, etc, and an epoch where the 'news' page-type with
    pattern '/elife-news/.../' ends on Mar 20th and the current '/news/...'
    starts Mar 21st, then the two-month chunk spanning Mar+Apr 2017 will
    become Mar(1st)+Mar(20th) and Mar(21st)+Apr"""

    # note: this is *not* how `elife.metrics.ga_metrics` works!
    # that module is doing a query for *every single day* since inception

    ensure(is_ptype(ptype), "bad page type")

    ptype_history = history or load_ptype_history(ptype)

    # until historical epochs are introduced, we only go back as far as
    # the beginning of the first time frame (elife 2.0)
    # start_date = start_date or settings.INCEPTION.date()
    start_date = tod(start_date or ptype_history['frames'][0]['starts'])
    end_date = tod(end_date or date.today())
    table_id = settings.GA_TABLE_ID

    ensure(is_date(start_date), "bad start date")
    ensure(is_date(end_date), "bad end date")

    query_template = {
        'ids': table_id,
        'max_results': 10000, # 10k is the max GA will ever return
        'start_date': None, # set later
        'end_date': None, # set later
        'metrics': 'ga:sessions', # *not* pageviews
        'dimensions': 'ga:pagePath,ga:date',
        'sort': 'ga:pagePath,ga:date',
        'filters': None, # set later,
        'include_empty_rows': False
    }

    # get a single list of months from date A (start) to date B (end)
    month_list = ga_utils.dt_month_range(start_date, end_date)

    # group the list into n-month chunks
    chunk_size = 2
    chunked_months = [month_list[i:i + chunk_size] for i in range(0, len(month_list), chunk_size)]

    # generate a list of queries we'll feed GA
    # use the start date from the first group, end date from the last group
    query_list = [merge(query_template, {"start_date": mgroup[0][0], "end_date": mgroup[-1][-1]}) for mgroup in chunked_months]

    # query list is still missing the pattern(s) that GA will query for.
    # until historical epochs are supported, we just use the first frame.
    # (frames are ordered descendingly, latest to earliest)
    frame = ptype_history['frames'][0]
    ptype_filter = frame.get('ga_pattern')
    if not ptype_filter:
        ensure('prefix' in frame, 'frame has no `ga_pattern` and no `prefix`, no query can be built')
        ptype_filter = generic_ga_filter(frame['prefix'])

    query_list = [(frame, merge(q, {"filters": ptype_filter})) for q in query_list]
    return query_list

@cached
def get_create_ptype(ptype):
    return first(create_or_update(models.PageType, {"name": ptype}, update=False))

@transaction.atomic
def update_page_counts(ptype, page_counts):
    def do(row):
        ptypeobj = get_create_ptype(ptype)

        page_data = {
            'type': ptypeobj,
            'identifier': row['identifier'],
        }
        pageobj = first(create_or_update(models.Page, page_data, update=False))

        pagecount_data = {
            'page': pageobj,
            'views': row['views'],
            'date': row['date']
        }
        pagecountobj = first(create_or_update(models.PageCount, pagecount_data, update=False))
        return pagecountobj
    return lmap(do, page_counts)

#
#
#

# naive, will change
def update_ptype(ptype):
    "glue code to query ga about a page-type and then processing and storing the results"
    try:
        for frame, query in build_ga_query(ptype):
            response = query_ga(ptype, query)
            normalised_rows = process_response(ptype, frame, response)
            counts = aggregate(normalised_rows)
            LOG.info("inserting/updating %s %ss" % (len(counts), ptype))
            update_page_counts(ptype, counts)
    except AssertionError as err:
        LOG.error(err)

#
#
#

def daily_page_views(pobj):
    qobj = pobj.pagecount_set.all() # daily is the finest grain we have
    sums = qobj.aggregate(views_sum=Sum('views'))
    return sums['views_sum'] or 0, qobj

def monthly_page_views(pobj):
    qobj = pobj.pagecount_set \
        .annotate(month=TruncMonth('date')) \
        .values('month') \
        .annotate(views_sum=Sum('views')) \
        .values('month', 'views_sum')
    sums = pobj.pagecount_set.all().aggregate(views_sum=Sum('views'))
    return sums['views_sum'], qobj

#
#
#

def page_views(pid, ptype, period=DAY):
    ensure(is_pid(pid), "bad page identifier", ValueError)
    ensure(is_ptype(ptype), "bad page type", ValueError)
    ensure(is_period(period), "bad period", ValueError)
    try:
        pobj = models.Page.objects.get(identifier=pid, type=ptype)
        dispatch = {
            DAY: daily_page_views,
            MONTH: monthly_page_views
        }
        return dispatch[period](pobj)
    except models.Page.DoesNotExist:
        return None
