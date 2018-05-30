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
import logging
from urllib.parse import urlparse
import importlib
from functools import partial
from collections import OrderedDict

LOG = logging.getLogger(__name__)
ORPHAN_LOG = logging.getLogger('orphans')

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
        dotted_path = dotted_path.strip().lower().replace('-', '_') # basic path normalisation
        package, funcname = dotted_path.rsplit('.', 1) # 'os.path.join' => 'os.path', 'join'
        package = importlib.import_module(package)
        ensure(hasattr(package, funcname),
               "could not find function %r in package %r for given path: %s" % (funcname, package, dotted_path))
        return getattr(package, funcname)
    except ImportError as err:
        # package doesn't exist
        LOG.debug(str(err))

    except AssertionError as err:
        # package exists but not function
        LOG.debug(str(err))
    return None

def asmaps(rows):
    "convenience, converts a list of GA result rows into dicts"
    return [dict(zip(['identifier', 'date', 'views'], row)) for row in rows]

def between(start, end, dt):
    return dt >= start and dt <= end

def normalise_path(path):
    return urlparse(path).path.lower()

def parse_map_file(ptype, frame, contents=None):

    def _parse_line(line):
        "the file is a simple 'cat nginx-redirect-file | grep prefix > outfile'"
        line = line.strip()
        if not line:
            return
        path, redirect = line.split("' '")
        path = path.strip(" '")
        redirect = redirect.strip(" ';")

        # TODO: the frame prefix is being overloaded here.
        # it's preventing frames that could have a simple query generated
        # use 'redirect-prefix' or similar instead
        prefix = frame['redirect-prefix']
        ensure(redirect.startswith(prefix), "redirect doesn't start with redirect-prefix: %s" % line)
        # /inside-elife/foobar => foobar
        bits = redirect.strip('/').split('/', 1)
        redirect = models.LANDING_PAGE if len(bits) == 1 else bits[1]
        return (path, redirect)
    path = os.path.join(settings.GA_PTYPE_SCHEMA_PATH, frame['path-map-file'])
    contents = (contents and contents.splitlines()) or open(path, 'r').readlines()
    return OrderedDict(lfilter(None, lmap(_parse_line, contents)))

#
#
#

def process_prefixed_path(prefix, path):
    path = normalise_path(path)
    ensure(path.startswith(prefix), "path does not start with given prefix (%r): %s" % (prefix, path), ValueError)
    # we could just dispense with the prefix and discard the first segment ...
    prefix_len = len(prefix)
    path = path[prefix_len:].strip().strip('/') # /events/foobar => foobar
    identifier = path.split('/', 1)[0] # foobar/the-baz-in-bar-fooed-at-the-star => foobar
    return identifier

def process_mapped_path(mapping, path):
    path = normalise_path(path)
    path in mapping or ORPHAN_LOG.info(path)
    return mapping.get(path)

def generic_results_processor(ptype, frame, rows):
    if 'path-map-file' in frame:
        mapping = parse_map_file(ptype, frame)
        path_processor = partial(process_mapped_path, mapping)
    elif 'prefix' in frame:
        path_processor = partial(process_prefixed_path, frame['prefix'])
    elif 'path-map' in frame:
        path_processor = partial(process_mapped_path, frame['path-map'])

    ensure(path_processor, "generic results processing requires a 'prefix' or 'path-map' key.")

    def _process(row):
        try:
            path, datestr, count = row
            identifier = path_processor(path)
            if not identifier:
                return # raise ValueError?
            return {
                'views': int(count),
                'date': _str2dt(datestr),
                'identifier': identifier,
            }
        except ValueError as err:
            LOG.info("skipping row, bad value: %s" % str(err))
        except BaseException as err:
            LOG.exception("unhandled exception processing row: %s", str(err), extra={"row": row})
    return list(filter(None, map(_process, rows)))

#
#
#

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

def process_response(ptype, frame, response):
    rows = response.get('rows')
    if not rows:
        LOG.warn("GA responded with no results", extra={'query': response['query'], 'ptype': ptype, 'frame': frame})
        return []

    # look for the "results_processor_frame_foo" function ...
    path = "metrics.{ptype}_type.results_processor_frame_{id}".format(ptype=ptype, id=frame['id'])

    # ... and use the generic processor if not found.
    results_processor = load_fn(path) or generic_results_processor

    normalised = results_processor(ptype, frame, rows)

    # todo: schema check normalised rows. should be easy

    return normalised

#
#
#

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

#
#
#

def generic_ga_filter(prefix):
    "returns a generic GA pattern that handles `/prefix` and `/prefix/what/ever` patterns"
    return "ga:pagePath=~^{prefix}$,ga:pagePath=~^{prefix}/.*$".format(prefix=prefix)

def generic_ga_filter_w_paths(prefix, path_list):
    stub = "ga:pagePath=~^{prefix}".format(prefix=prefix)

    def mk(path):
        return (stub + "/{path}$").format(path=path.lstrip('/'))
    ql = ",".join(map(mk, path_list))
    if prefix:
        return "{landing}$,{enum}".format(landing=stub, enum=ql)
    return ql

def apply_query_to_list(ptype_filter, query_list):
    query_list = [merge(query, {"filters": ptype_filter}) for query in query_list]
    return query_list

def generic_query_processor(ptype, frame, query_list):
    # NOTE: ptype is unused here here, it's just to match a query processor function's signature
    ptype_filter = frame.get('pattern')
    if frame.get('prefix') and frame.get('path-list'):
        ptype_filter = generic_ga_filter_w_paths(frame['prefix'], frame['path-list'])
    elif frame.get('prefix'):
        ptype_filter = generic_ga_filter(frame['prefix'])
    elif frame.get('path-map'):
        ptype_filter = generic_ga_filter_w_paths('', frame['path-map'].keys())
    return apply_query_to_list(ptype_filter, query_list)

#
#
#

def build_ga_query__frame_month_range(ptype, start_date=None, end_date=None, history_data=None):
    "returns a list of frame+month-range pairs. each month-range is itself a pair of start-date+end-date"
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

    def interesting_frames(frame):
        "do the start or end dates cross the frame boundary? if so, we're interested in it"
        date_in_frame = partial(between, frame['starts'], frame['ends'])
        return date_in_frame(start_date) or date_in_frame(end_date)

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

    # we now have a solid datastructure to generate queries from
    # [(f1, [(d1, d2), (d3, d4), (d5, d6)]), (f2, [(d7, d8)]), (fN, [...])]

    return month_list

# sigh: I've just discovered GA *does* have pagination. it uses 'start-index' and 'max-results'
# I wonder why I never questioned my assumption it didn't?
# chunking by month to reduce result count still works nicely, but transparent pagination would be nicer
# update: it's also keeping transaction size (and thus memory size) down when we get into thousands of views per-month.
# I could partition transaction size on num objects though ...
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
    path = "metrics.{ptype}_type.query_processor_frame_{id}".format(ptype=ptype, id=frame['id'])

    # ... and use the generic query processor if not found.
    query_processor = load_fn(path) or generic_query_processor

    # update the list of queries with a 'filters' value appropriate to type and frame
    return query_processor(ptype, frame, query_list)

def build_ga_query(ptype, start_date=None, end_date=None, history_data=None):
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

    # glue code as original function became huge

    # returns a list of pairs:
    # [(frame1, [(month1-min, month1-max), (m2-min, m2-max), (m3-min, m3-max)]),
    #  (frame2, [(...), ...])]
    frame_month_list = build_ga_query__frame_month_range(ptype, start_date, end_date, history_data)

    # each time frame will require it's own pattern generation, post processing and normalisation
    # we can generate 90% of that query here:
    query_list = [(frame, build_ga_query__queries_for_frame(ptype, frame, month_list)) for frame, month_list in frame_month_list]

    return query_list

#
#
#

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
        for frame, query_list in build_ga_query(ptype):
            for i, query in enumerate(query_list):
                response = query_ga(ptype, query)
                # TODO: issue an alert/notice when size of results gets within 1k of the max 10k
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
