from datetime import datetime
from . import elife_v1, utils
from article_metrics.utils import ensure, lfilter
import re
import logging

LOG = logging.getLogger(__name__)

def path_counts_query(table_id, from_date, to_date):
    "a GA4 query using the same path regex from elife-v6"

    explanation = (
        # captures all articles
        "^/articles/[0-9]+"
        # including executable articles
        "(/executable)?"
        # opens optional section for matching url parameters
        "("
        # literal '?' matches the beginning of the url parameters
        # but because they're so mangled we also need to optionally match '&'
        "(\\?|&){1}"
        # non-greedy match of any other url parameter(s) between the start of the section and the ones we're looking for.
        ".*?"
        # match any of the patterns below at least once.
        "(twclid|utm_campaign|utm_source=content_alert)+"
        # non-greedy match of any other url parameter(s) between the end of our match and the end of the url
        ".*?"
        # optional section for matching url parameters should be matched zero or one times
        ")?"
        # matches the end of the url.
        # if we don't stop the matching here it goes on to match anything.
        "$"
    )
    ga_filter = "^/articles/[0-9]+(/executable)?((\\?|&){1}.*?(twclid|utm_campaign|utm_source=content_alert)+.*?)?$"
    assert ga_filter == explanation, "explanation of filter differs from the actual filter."

    return {"dimensions": [{"name": "pagePathPlusQueryString"}],
            "metrics": [{"name": "sessions"}],
            "dateRanges": [{"startDate": utils.ymd(from_date),
                            "endDate": utils.ymd(to_date)}],
            "dimensionFilter": {
                "filter": {
                    "fieldName": "pagePathPlusQueryString",
                    "stringFilter": {
                        "matchType": "FULL_REGEXP",
                        "value": ga_filter}}},
            "limit": "10000"}

# ...python *does* support {n,m} though, so we can filter bad article IDs in post
# lsh@2021-11-30: still true.
# parse the article ID from a path that may include an optional '/executable'.
REGEX = r"/articles/(?P<artid>\d{1,6})"
PATH_RE = re.compile(REGEX, re.IGNORECASE)

def path_count(row):
    """given a `row`, returns a triple of (art-id, count-type, count) or `None`.

    Each `row` looks like:

    {
      "dimensionValues": [
        {
          "value": "/articles/48822"
        }
      ],
      "metricValues": [
        {
          "value": "3"
        }
      ]
    }
    """
    try:
        ensure(len(row['dimensionValues']) == 1, "row with unexpected number of dimensionValues found: %s" % row)
        ensure(len(row['metricValues']) == 1, "row with unexpected number of metricValues found: %s" % row)
        path = row['dimensionValues'][0]['value']
        count = row['metricValues'][0]['value']
        regex_obj = re.match(PATH_RE, path.lower())
        ensure(regex_obj, "unhandled path: %s" % row)
        # "/articles/12345/executable" => {'artid': 12345}
        data = regex_obj.groupdict()
        count_type = 'full' # vs 'abstract' or 'digest', from previous eras
        return data['artid'], count_type, int(count)
    except AssertionError as exc:
        LOG.debug("ignoring row (views), failed expections", exc_info=exc)

def path_counts(path_count_pairs):
    "takes a list of rows from GA4 and groups by msid, returning a list of (msid, count-type, count)"
    path_count_triples = lfilter(None, [path_count(pair) for pair in path_count_pairs])
    return elife_v1.group_results(path_count_triples)

def event_counts_query(table_id, from_date, to_date):
    "returns the raw GA results for PDF downloads between the two given dates"
    ensure(isinstance(from_date, datetime), "'from' date must be a datetime object. received %r" % from_date)
    ensure(isinstance(to_date, datetime), "'to' date must be a datetime object. received %r" % to_date)
    return {
        "dimensions": [
            {"name": "eventName"},
            {"name": "pagePath"}
        ],
        "metrics": [
            {"name": "eventCount"}
        ],
        "dateRanges": [
            {"startDate": from_date, "endDate": to_date}
        ],
        "dimensionFilter": {
            "andGroup": {
                "expressions": [
                    {
                        "filter": {
                            "fieldName": "eventName",
                            "stringFilter": {
                                "matchType": "EXACT",
                                "value": "Download"
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
                    }
                ]
            }
        },
        "limit": 10000
    }

def event_count(row):
    """
    row looks like:
    {
        "dimensionValues": [
            {
                "value": "Download"
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
        ensure(len(row['dimensionValues']) == 2, "row with unexpected number of dimensionValues found: %s" % row)
        ensure(len(row['metricValues']) == 1, "row with unexpected number of metricValues found: %s" % row)
        path = row['dimensionValues'][1]['value']
        count = row['metricValues'][0]['value']
        bits = path.split('/') # ['', 'articles', '80092']
        return bits[2], int(count)
    except AssertionError as exc:
        LOG.debug("ignoring row (downloads), failed expections", exc_info=exc)

def event_counts(row_list):
    "parses the list of rows returned by google to extract the doi and it's count"
    # note: figures downloads (/articles/80082/figures) and mixed case paths (/Articles/800082) are excluded via the GA query.
    # for example, a case where two rows for 80072, one downloads, one figure downloads resulting in:
    #   [(80082, 717), (80082, 2)]
    # and reducing to
    #   {80082: 2}
    # won't occur unless we manipulate the GA results.
    return dict(map(event_count, row_list))
