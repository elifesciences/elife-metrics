from urllib.parse import urlparse
from functools import partial
from datetime import datetime, date
from article_metrics.utils import ensure
from article_metrics.ga_metrics import core as ga_core
from article_metrics import utils as ga_utils
import logging

LOG = logging.getLogger(__name__)

def build_ga4_query__queries_for_frame(_, frame, start_date, end_date):
    """returns a list of GA4 query maps for the given `frame` and for the given date range.
    the date range may fall inside or outside of the frame's own boundaries.
    if the date range is outside of the frame's boundaries the range is capped.
    """
    ensure(isinstance(start_date, date), "'start' date must be a datetime object. received %r" % start_date)
    ensure(isinstance(end_date, date), "'end' date must be a datetime object. received %r" % end_date)

    # lsh@2023-02-13: there are no frames more complex than the 'prefix' anymore.
    # pull any other logic in from ga3.py and dispatch as necessary.
    ensure('prefix' in frame, "frame with id %r has no 'prefix' key. ga4 only supported on frames using a simple prefix." % frame['id'])
    prefix = frame['prefix']

    # cap the given date range (start_date, end_date) to frame boundaries if they extend beyond them.
    start_date = frame['starts'] if start_date < frame['starts'] else start_date
    end_date = frame['ends'] if end_date > frame['ends'] else end_date

    # https://developers.google.com/analytics/devguides/reporting/data/v1
    # https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema
    return {"dimensions": [{"name": "date"},
                           {"name": "pagePathPlusQueryString"}],
            "metrics": [{"name": "sessions"}],
            # TODO: orderBys
            "dateRanges": [{"startDate": ga_utils.ymd(start_date),
                            "endDate": ga_utils.ymd(end_date)}],
            "dimensionFilter": {
                "filter": {
                    "fieldName": "pagePathPlusQueryString",
                    "stringFilter": {
                        "matchType": "BEGINS_WITH",
                        "value": prefix}}},
            "orderBys": [
                {"desc": True,
                 "dimension": {"dimensionName": "date",
                               "orderType": "NUMERIC"}}],
            "limit": "10000"}

def query_ga(ptype, query, replace_cache_files=False):
    start_dt = ga_utils.todt(query['dateRanges'][0]['startDate'])
    end_dt = ga_utils.todt(query['dateRanges'][0]['endDate'])

    results_type = ptype
    results, _ = ga_core.query_ga_write_results_v2(query, start_dt, end_dt, results_type)
    return results

# --- processing

def prefixed_path_id(prefix, path):
    """returns the 'foo' portion of a given `path` like '/events/foo', but only if `path` starts with `prefix`.
    longer paths like '/events/foo/bar' or paths with query parameters like '/events/foo?bar=bar' will still
    only return the 'foo' portion."""
    path = urlparse(path).path.lower() # normalise
    ensure(path.startswith(prefix), "path does not start with given prefix (%r): %s" % (prefix, path), ValueError)
    path = path[len(prefix):].strip().strip('/') # /events => '', /events/foobar => foobar, /events/foo/bar/ => foo/bar
    identifier = path.split('/', 1)[0] # '' => '', foobar => foobar, foo/bar => foo
    return identifier

def process_response(ptype, frame, response):
    rows = response.get('rows')
    if not rows:
        LOG.warning("GA responded with no results", extra={'query': response['query'], 'ptype': ptype, 'frame': frame})
        return []

    id_fn = partial(prefixed_path_id, frame['prefix'])

    def _process(row):
        try:
            datestr = row['dimensionValues'][0]['value']
            path = row['dimensionValues'][1]['value']
            count = row['metricValues'][0]['value']
            identifier = id_fn(path)
            return {
                'views': int(count),
                'date': datetime.strptime(datestr, "%Y%m%d").date(),
                'identifier': identifier
            }
        except ValueError as err:
            LOG.error("skipping row, bad value: %s" % str(err))
        except Exception as err:
            LOG.exception("unhandled exception processing row: %s", str(err), extra={"row": row})

    return list(filter(None, map(_process, rows)))
