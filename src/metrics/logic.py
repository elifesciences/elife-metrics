from . import models, history, ga3, ga4
from article_metrics.utils import ensure, lmap, create_or_update, first, ymd, lfilter, run
from article_metrics.ga_metrics import core as ga_core
from django.db.models import Sum, F
from django.db.models.functions import TruncMonth
from django.conf import settings
from datetime import date, datetime
from django.db import transaction
import os
import logging
from urllib.parse import urlparse
from functools import partial
from collections import OrderedDict

LOG = logging.getLogger(__name__)

DAY, MONTH = 'day', 'month'

MAX_GA_RESULTS = 10000

GA4_SWITCH_DATE = ga_core.GA4_SWITCH.date()

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

def mkidx(rows, keyfn):
    idx = {}
    for row in rows:
        key = keyfn(row)
        group = idx.get(key, [])
        group.append(row)
        idx[key] = group
    return idx

def asmaps(rows):
    "convenience, converts a list of GA result rows into dicts"
    return [dict(zip(['identifier', 'date', 'views'], row)) for row in rows]

def normalise_path(path):
    return urlparse(path).path.lower()

def parse_map_file(frame, contents=None):
    contents and ensure(isinstance(contents, str), "'contents' must be a string'")

    def _parse_line(line):
        "the file is a simple 'cat nginx-redirect-file | grep prefix > outfile'"
        line = line.strip()
        if not line:
            return
        path, redirect = line.split("' '")
        path, redirect = path.strip(" '"), redirect.strip(" ';")
        prefix = frame['redirect-prefix']
        ensure(redirect.startswith(prefix), "redirect doesn't start with redirect-prefix: %s" % line)
        # /inside-elife/foobar => foobar
        bits = redirect.strip('/').split('/', 1) # '/inside-elife/foobar' -> 'inside-elife/foobar' -> ['inside-elife, 'foobar']
        redirect = models.LANDING_PAGE if len(bits) == 1 else bits[1]
        return (path, redirect)
    if contents:
        contents = contents.splitlines()
    else:
        path = os.path.join(settings.GA_PTYPE_SCHEMA_PATH, frame['path-map-file'])
        contents = open(path, 'r').readlines()
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
    return mapping.get(path)

def generic_results_processor(ptype, frame, rows):

    # TODO: will need to differentiate between ga3 and ga4 results

    if 'path-map-file' in frame:
        mapping = parse_map_file(frame)
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
            if identifier is None:
                return # raise ValueError?
            return {
                'views': int(count),
                'date': datetime.strptime(datestr, "%Y%m%d").date(),
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
    rows = [(grp[0]['identifier'], grp[0]['date'], sum(map(lambda d: d.get('views'), grp))) for grp in idx.values()]
    rows = asmaps(rows)

    # sort rows by date and then path
    # not necessary, but makes output nicer
    rows = sorted(rows, key=lambda r: ymd(r['date']) + r['identifier'], reverse=True) # DESC

    return rows

def process_response(ptype, frame, response):

    rows = response.get('rows')
    if not rows:
        LOG.warning("GA responded with no results", extra={'query': response['query'], 'ptype': ptype, 'frame': frame})
        return []

    # look for the "results_processor_frame_foo" function ...
    #path = "metrics.{ptype}_type.results_processor_frame_{id}".format(ptype=ptype, id=frame['id'])

    # ... and use the generic processor if not found.
    #results_processor = load_fn(path) or generic_results_processor

    # lsh@2023-02-13: nothing ever used the per-page-type results processor.
    # instead it looks like `generic_results_processor` got fat attempting to handle everything.
    results_processor = generic_results_processor

    normalised = results_processor(ptype, frame, rows)

    # todo: schema check normalised rows. should be easy

    return normalised

# ---

def build_ga_query__queries_for_frame(ptype, frame, start_date, end_date):
    """
    the big ga3 to ga4 switch.
    ga3.py has lots of query generation logic, probably over engineered
    ga4.py is much the same
    both should return results that can be processed with the `process_response` logic above.
    """
    era = ga_core.GA3 if end_date <= GA4_SWITCH_DATE else ga_core.GA4
    if era == ga_core.GA3:
        return ga3.build_ga3_query__queries_for_frame(ptype, frame, start_date, end_date)
    return ga4.build_ga4_query__queries_for_frame(ptype, frame, start_date, end_date)

# ---

def query_ga(ptype, query, results_pp=MAX_GA_RESULTS, replace_cache_files=False):
    ensure('end_date' in query, "query missing 'end_date' field")
    end_date = query['end_date']
    # urgh. todo?
    if not is_date(end_date):
        end_date = datetime.strptime(query['end_date'], '%Y-%m-%d').date()
    era = ga_core.GA3 if end_date <= GA4_SWITCH_DATE else ga_core.GA4
    if era == ga_core.GA3:
        return ga3.query_ga(ptype, query, results_pp, replace_cache_files)
    return ga4.query_ga(ptype, query, results_pp, replace_cache_files)

# ---

def interesting_frames(start_date, end_date, frame_list):
    "do the start or end dates cross the frame boundary? if so, we're interested in it"
    def _interesting_frame(frame):
        if frame['starts'] < start_date and frame['ends'] < start_date:
            return False
        if frame['ends'] > end_date and frame['starts'] > end_date:
            return False
        return True
    return lfilter(_interesting_frame, frame_list)


def build_ga_query(ptype, start_date=None, end_date=None):
    """As we go further back in history the query will change as known epochs
    overlap. These overlaps will truncate the current period to the epoch
    boundaries."""

    ensure(is_ptype(ptype), "bad page type")

    # if dates given, ensure they are date objects
    start_date and ensure(is_date(start_date), "bad start date")
    end_date and ensure(is_date(end_date), "bad end date")

    # extract just the page type we're after.
    history_data = history.ptype_history(ptype)
    frame_list = history_data['frames']

    # frames are ordered oldest to newest (asc)
    earliest_date = frame_list[0]['starts']
    latest_date = frame_list[-1]['ends']

    start_date = start_date or earliest_date
    end_date = end_date or latest_date
    ensure(start_date <= end_date, "start date %r cannot be greater than end date %r" % (start_date, end_date))

    # only those frames that overlap our start/end dates
    frame_list = interesting_frames(start_date, end_date, frame_list)

    # each timeframe requires it's own pattern generation, post processing and normalisation
    query_list = [(frame, build_ga_query__queries_for_frame(ptype, frame, start_date, end_date)) for frame in frame_list]

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
        key_list = ['page', 'date']
        pagecountobj = first(create_or_update(models.PageCount, pagecount_data, key_list, update=True))
        return pagecountobj
    return lmap(do, page_counts)

#
#
#

def update_ptype(ptype, replace_cache_files=False):
    "query GA about a page-type and then processing and storing the results"
    try:
        for frame, query in build_ga_query(ptype):
            response = query_ga(ptype, query, replace_cache_files=replace_cache_files)
            normalised_rows = process_response(ptype, frame, response)
            counts = aggregate(normalised_rows)
            LOG.info("inserting/updating %s '%s' rows" % (len(counts), ptype))
            update_page_counts(ptype, counts)
    except AssertionError as err:
        LOG.error(err)

def update_all_ptypes():
    run(update_ptype, models.PAGE_TYPES)

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
