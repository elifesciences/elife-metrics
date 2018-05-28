from . import models, history
from article_metrics.utils import ensure, lmap, create_or_update, first, merge, ymd, lfilter
from article_metrics.ga_metrics import core as ga_core, utils as ga_utils
from django.db.models import Sum, F
from django.db.models.functions import TruncMonth
from django.conf import settings
from datetime import date, datetime
from django.db import transaction
import json
import os
from functools import partial
import logging
from urllib.parse import urlparse
import importlib

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
    return datetime.strptime(string, "%Y%m%d").date()

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

def load_fn(dotted_path):
    try:
        package, funcname = dotted_path.rsplit('.', 1) # 'os.path.join' => 'os.path', 'join'
        package = importlib.import_module(package)
        ensure(hasattr(package, funcname),
               "could not find function %r in package %r for given path: %s" % (funcname, package, dotted_path))
        return getattr(package, funcname)
    except ImportError as err:
        # package doesn't exist
        LOG.warn(str(err))

    except AssertionError as err:
        # package exists but not function
        LOG.warn(str(err))
    return None

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
        try:
            path, datestr, count = row
            path = process_path(prefix, path)
            return {
                'views': int(count),
                'date': _str2dt(datestr),
                'identifier': path,
            }
        except BaseException as err:
            LOG.exception("unhandled exception processing row: %s", str(err), extra={"row": row})
    return list(filter(None, map(_process, rows)))

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
    rows = response.get('rows')
    if not rows:
        LOG.warn("GA responded with no results", extra={'query': response['query'], 'ptype': ptype, 'frame': frame})
        return []
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
    normalised = processor(rows)
    return normalised

def query_ga(ptype, query):
    sd, ed = query['start_date'], query['end_date']
    LOG.info("querying GA for %ss between %s and %s" % (ptype, sd, ed))
    dump_path = ga_core.output_path(ptype, sd, ed)
    if os.path.exists(dump_path):
        # temporary caching while I debug
        LOG.debug("(cache hit)")
        return json.load(open(dump_path, 'r'))
    raw_response = ga_core.query_ga(query) # potentially 10k worth, but in actuality ...
    ga_core.write_results(raw_response, dump_path)
    return raw_response

def generic_ga_filter(prefix):
    "returns a generic GA pattern that handles `/prefix` and `/prefix/what/ever` patterns"
    return "ga:pagePath=~^{prefix}$,ga:pagePath=~^{prefix}/.*$".format(prefix=prefix)

#
#
#

def generic_query_processor(ptype, frame, query_list):
    ptype_filter = frame.get('pattern')
    if not ptype_filter:
        ensure('prefix' in frame, 'frame has no `pattern` and no `prefix`, no query can be built')
        ptype_filter = generic_ga_filter(frame['prefix'])
    query_list = [merge(q, {"filters": ptype_filter}) for q in query_list]
    return query_list

#
#
#

def build_ga_query__frame_month_range(ptype, start_date=None, end_date=None, history_data=None):
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

    ensure(is_ptype(ptype), "bad page type")

    # if dates given, ensure they are date objects
    start_date and ensure(is_date(start_date), "bad start date")
    end_date and ensure(is_date(end_date), "bad end date")

    # if history data provided, ensure it validates
    if history_data:
        history_data = history.type_object.validate(history_data)

    # extract just the page type we're after
    ptype_history = history_data or history.ptype_history(ptype)
    frame_list = ptype_history['frames']

    # frames are ordered oldest to newest (asc)
    earliest_date = frame_list[0]['starts']
    latest_date = frame_list[-1]['ends']

    start_date = start_date or earliest_date
    end_date = end_date or latest_date
    ensure(start_date <= end_date, "start date %r cannot be greater than end date %r" % (start_date, end_date))

    def between(s, e, d):
        return d >= s and d <= e

    def interesting_frames(frame):
        "do the start or end dates cross the frame boundary? if so, we're interested in it"
        return between(frame['starts'], frame['ends'], start_date) or between(frame['starts'], frame['ends'], end_date)

    # only those frames that overlap our start/end dates
    frame_list = lfilter(interesting_frames, frame_list)

    def frame_month_range(frame):
        "returns a (frame, month list) pair. month list is capped to start and end dates"
        r_start = start_date if start_date >= frame['starts'] else frame['starts']
        r_end = end_date if end_date <= frame['ends'] else frame['ends']
        month_list = ga_utils.dt_month_range(r_start, r_end, preserve_caps=True)
        # saves some datetime wrangling later and prevents further changes
        month_list = [(mmin.date(), mmax.date()) for mmin, mmax in month_list]
        return (frame, month_list)

    # expand each frame (f):
    # [(f1, [(d1, d2), (d3, d4), (d5, d6)]),
    #  (f2, [(d7, d8)]),
    #  (fN, [...])]
    month_list = lmap(frame_month_range, frame_list)

    print('month lists:', month_list)
    print()

    # we now have a solid datastructure to generate queries from
    # [(f1, [(d1, d2), (d3, d4), (d5, d6)]), (f2, [(d7, d8)]), (fN, [...])]

    return month_list

def build_ga_query__queries_for_frame(ptype, frame, month_list):
    "within a frame's month list we can safely chunk results without overlapping other frames"

    # re-group the list into n-month chunks
    chunk_size = 2
    chunked_months = [month_list[i:i + chunk_size] for i in range(0, len(month_list), chunk_size)]

    query_template = {
        'ids': settings.GA_TABLE_ID,
        'max_results': 10000, # 10k is the max GA will ever return
        'start_date': None, # set later
        'end_date': None, # set later
        'metrics': 'ga:sessions', # *not* pageviews
        'dimensions': 'ga:pagePath,ga:date',
        'sort': 'ga:pagePath,ga:date',
        'filters': None, # set later,
        'include_empty_rows': False
    }

    # use the start date from the first group, end date from the last group
    query_list = [merge(query_template, {"start_date": mgroup[0][0], "end_date": mgroup[-1][-1]}) for mgroup in chunked_months]

    # look for the "query_processor_frame_foo" function ...
    path = "metrics.{ptype}.query_processor_frame_{id}".format(ptype=ptype, id=frame['id'])
    # ... and use the generic query processor if not found.
    query_processor = load_fn(path) or generic_query_processor

    # update the query list with per-type, per-frame patterns
    return query_processor(ptype, frame, query_list)

def build_ga_query(ptype, start_date=None, end_date=None, history_data=None):

    # gives us a list of pairs:
    # [(frame1, [(month1-min, month1-max), (m2-min, m2-max), (m3-min, m3-max)]),
    #  (frame2, [(...), ...])]
    frame_month_list = build_ga_query__frame_month_range(ptype, start_date, end_date, history_data)

    # each time frame will require it's own pattern generation, post processing and normalisation
    # we can generate 90% of that query here:
    query_list = [(frame, build_ga_query__queries_for_frame(ptype, frame, month_list)) for frame, month_list in frame_month_list]

    # TODO: just the per-type, per-frame dispatch to go
    # I'm thinking:
    # query_list = ptype.preprocessor(frame, query)"

    # the output should be a list of queries to run.
    # we can supplement that list of queries with a processor function or whatever

    # each frame has an optional ID value that we can use to find a pre and post processor function
    # if frame is missing this ID, attempt default processing of results
    # ideally, everything prior to 2.0 should have an ID

    return query_list

@transaction.atomic
def update_page_counts(ptype, page_counts):
    ptypeobj = first(create_or_update(models.PageType, {"name": ptype}, update=False))

    def do(row):
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

def update_all_ptypes():
    lmap(update_ptype, models.PAGE_TYPES)

#
#
#

def daily_page_views(pobj):
    # create an alias 'date_field'.
    # allows consistent chopping and sorting of results between daily and monthly
    qobj = pobj.pagecount_set.all().annotate(date_field=F('date'))
    sums = qobj.aggregate(views_sum=Sum('views'))
    return sums['views_sum'] or 0, qobj

def monthly_page_views(pobj):
    qobj = pobj.pagecount_set \
        .annotate(date_field=TruncMonth('date')) \
        .values('date_field') \
        .annotate(views_sum=Sum('views')) \
        .values('date_field', 'views_sum') \
        .order_by()
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
