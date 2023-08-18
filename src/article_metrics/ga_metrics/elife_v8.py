from functools import reduce
from datetime import datetime
from . import elife_v7, utils
from article_metrics.utils import ensure
import logging

LOG = logging.getLogger(__name__)

# lsh@2023-08-16: switch from `Download` events to `file_download` events.
# event counting is _slightly_ different to v7 as well.
# view counting has stayed the same.
path_counts_query = elife_v7.path_counts_query
path_counts = elife_v7.path_counts

def event_counts_query(table_id, from_date, to_date):
    "returns the raw GA results for PDF downloads between the two given dates"
    ensure(isinstance(from_date, datetime), "'from' date must be a datetime object. received %r" % from_date)
    ensure(isinstance(to_date, datetime), "'to' date must be a datetime object. received %r" % to_date)
    return {
        "metrics": [
            {"name": "eventCount"},
        ],
        "dimensions": [
            {"name": "eventName"},
            {"name": "fileExtension"},
            {"name": "pagePath"},
        ],
        "orderBys": [
            {"desc": False,
             "dimension": {"dimensionName": "pagePath",
                           "orderType": "ALPHANUMERIC"}}
        ],
        "dateRanges": [
            {"startDate": utils.ymd(from_date),
             "endDate": utils.ymd(to_date)}
        ],
        "dimensionFilter": {
            "andGroup": {
                "expressions": [
                    {
                        "filter": {
                            "fieldName": "eventName",
                            "stringFilter": {
                                "matchType": "EXACT",
                                "value": "file_download"
                            }
                        }
                    },
                    {
                        "filter": {
                            "fieldName": "pagePath",
                            "stringFilter": {
                                "matchType": "FULL_REGEXP",
                                "value": "^/articles/\\d+$",
                                "caseSensitive": True
                            },
                        }
                    },
                    {
                        "filter": {
                            "fieldName": "fileExtension",
                            "stringFilter": {
                                "matchType": "EXACT",
                                "value": "pdf",
                            }
                        }
                    },
                ]
            }
        },
        "limit": 10000
    }

def event_count(row):
    """returns a pair of (path, download-count) from given `row`.

    `row` looks like:
    {
        "dimensionValues": [
            {
                "value": "file_download"
            },
            {
                "value": "/articles/80092"
            }
        ],
        "metricValues": [
            {
                "value": "717"
            }
        ]
    }
    """
    try:
        ensure(len(row['dimensionValues']) == 3, "row with unexpected number of dimensionValues found: %s" % row)
        ensure(len(row['metricValues']) == 1, "row with unexpected number of metricValues found: %s" % row)
        path = row['dimensionValues'][2]['value']
        count = row['metricValues'][0]['value']
        ensure(path != "(other)", "found 'other' row with value '%s'. GA has aggregated rows because query returned too much data." % count)
        bits = path.split('/') # ['', 'articles', '80092']
        ensure(len(bits) == 3, "failed to find a valid path: %s" % path)
        return int(bits[2]), int(count)
    except AssertionError as exc:
        LOG.warning("ignoring article downloads row: %s" % exc, extra={'row': row})
    except Exception as exc:
        LOG.warning("unhandled exception parsing download event, ignoring row: %s" % exc, extra={'row': row})

def event_counts(row_list):
    "parses the list of rows returned by google to extract the doi and it's count"
    # note: figures downloads (/articles/80082/figures) and mixed case paths (/Articles/800082) are excluded via the GA query.
    # for example, a case where two rows for 80072, one downloads, one figure downloads resulting in:
    #   [(80082, 717), (80082, 2)]
    # and reducing to
    #   {80082: 719}
    # shouldn't occur.
    counts = filter(None, map(event_count, row_list or []))

    def aggr(dic, pair):
        msid, count = pair
        doi = utils.msid2doi(msid)
        dic[doi] = dic.get(doi, 0) + count
        return dic
    return reduce(aggr, counts, {})
