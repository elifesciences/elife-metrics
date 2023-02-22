from . import models
from datetime import datetime
from urllib.parse import urlparse
from functools import partial
from collections import OrderedDict


import importlib
from article_metrics.utils import ensure, lmap, lfilter
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

def generic_query_processor(_, frame):
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


# results processing


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


def process_response(ptype, frame, response):
    if not response.get('rows'):
        LOG.warning("GA responded with no results", extra={'query': response['query'], 'ptype': ptype, 'frame': frame})
        return []

    rows = response.get('rows')

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
