from datetime import datetime
from article_metrics.utils import ensure
from article_metrics.ga_metrics import core as ga_core, utils as ga_utils
import logging

LOG = logging.getLogger(__name__)

def build_ga4_query__queries_for_frame(_, frame, start_date, end_date):
    ensure(isinstance(start_date, datetime), "'start' date must be a datetime object. received %r" % start_date)
    ensure(isinstance(end_date, datetime), "'end' date must be a datetime object. received %r" % end_date)

    # lsh@2023-02-13: there are no frames more complex than the 'prefix' anymore.
    # pull any other logic in from ga3.py and dispatch as necessary.

    prefix = frame['prefix']

    # https://developers.google.com/analytics/devguides/reporting/data/v1
    # https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema
    return {"dimensions": [{"name": "pagePathPlusQueryString"}],
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
            "limit": "10000"}

def query_ga(ptype, query, results_pp=None, replace_cache_files=False):
    ensure(not results_pp, "results_pp is ignored") # because it's *always* fixed at 10k

    # urgh
    start_dt = ga_utils.todt(query['dateRanges'][0]['startDate'])
    end_dt = ga_utils.todt(query['dateRanges'][0]['endDate'])

    results, output_path = ga_core.query_ga_write_results2(query, start_dt, end_dt, ptype)
    return results

def process_response(ptype, frame, response):
    if not response.get('rows'):
        LOG.warning("GA responded with no results", extra={'query': response['query'], 'ptype': ptype, 'frame': frame})
        return []
    return []
