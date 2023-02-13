from datetime import datetime
from article_metrics.utils import ensure

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


def build_ga4_query__queries_for_frame(ptype, frame, start_date, end_date):
    ensure(isinstance(start_date, datetime), "'start' date must be a datetime object. received %r" % start_date)
    ensure(isinstance(end_date, datetime), "'end' date must be a datetime object. received %r" % end_date)

    ga_filter = ""

    query = {"dimensions": [{"name": "pagePathPlusQueryString"}],
             "metrics": [{"name": "sessions"}],
             # TODO: orderBys
             "dateRanges": [{"startDate": '...',
                            "endDate": '...'}],
             "dimensionFilter": {
        "filter": {
            "fieldName": "pagePathPlusQueryString",
            "stringFilter": {
                "matchType": "FULL_REGEXP",
                "value": ga_filter}}},
             "limit": "10000"}

    # look for the "query_processor_frame_foo" function ...
    #path = "metrics.{ptype}_type.query_processor_frame_{id}".format(ptype=ptype, id=frame['id'])

    # ... and use the generic query processor if not found.
    #query_processor = load_fn(path) or generic_query_processor
    query_processor = generic_query_processor

    # update the query with a 'filters' value appropriate to type and frame
    query['filters'] = query_processor(ptype, frame)

    return query
