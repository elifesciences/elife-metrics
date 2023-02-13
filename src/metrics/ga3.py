import importlib
from article_metrics.utils import ensure
from article_metrics.ga_metrics import core as ga_core
from django.conf import settings
import json
import os
import logging

LOG = logging.getLogger(__name__)

DAY, MONTH = 'day', 'month'

MAX_GA_RESULTS = 10000

def is_inrange(v, a, b):
    return isinstance(v, int) and v >= a and v <= b

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


def query_ga(ptype, query, results_pp=MAX_GA_RESULTS, replace_cache_files=False):
    ensure(is_inrange(results_pp, 1, MAX_GA_RESULTS), "`results_pp` must be an integer between 1 and %s" % MAX_GA_RESULTS)
    sd, ed = query['start_date'], query['end_date']
    LOG.info("querying GA for %ss between %s and %s" % (ptype, sd, ed))
    dump_path = ga_core.output_path(ptype, sd, ed)
    # TODO: this settings.TESTING check is a code smell.
    if os.path.exists(dump_path) and not settings.TESTING:
        if not replace_cache_files:
            LOG.info("(cache hit)")
            return json.load(open(dump_path, 'r'))
        # cache file will be replaced with results
        pass

    query['max_results'] = results_pp
    query['start_index'] = 1
    response = ga_core.query_ga(query)
    if not settings.TESTING:
        ga_core.write_results(response, dump_path)
    return response

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

def generic_query_processor(ptype, frame):
    # NOTE: ptype is unused, it's just to match a query processor function's signature
    ptype_filter = None
    if frame.get('pattern'):
        ptype_filter = frame['pattern']
    elif frame.get('prefix') and frame.get('path-list'):
        ptype_filter = generic_ga_filter_w_paths(frame['prefix'], frame['path-list'])
    elif frame.get('prefix'):
        ptype_filter = generic_ga_filter(frame['prefix'])
    elif frame.get('path-map'):
        ptype_filter = generic_ga_filter_w_paths('', frame['path-map'].keys())
    ensure(ptype_filter, "bad frame data")
    return ptype_filter

def build_ga3_query__queries_for_frame(ptype, frame, start_date, end_date):
    query = {
        'ids': settings.GA3_TABLE_ID,
        'max_results': MAX_GA_RESULTS,
        'metrics': 'ga:uniquePageviews', # *not* sessions, nor regular pageviews
        'dimensions': 'ga:pagePath,ga:date',
        'sort': 'ga:pagePath,ga:date',
        'include_empty_rows': False,

        'start_date': frame['starts'] if start_date < frame['starts'] else start_date,
        'end_date': frame['ends'] if end_date > frame['ends'] else end_date,

        # set by the `query_processor`
        'filters': None,
    }

    # look for the "query_processor_frame_foo" function ...
    path = "metrics.{ptype}_type.query_processor_frame_{id}".format(ptype=ptype, id=frame['id'])

    # ... and use the generic query processor if not found.
    query_processor = load_fn(path) or generic_query_processor

    # update the query with a 'filters' value appropriate to type and frame
    query['filters'] = query_processor(ptype, frame)

    return query
