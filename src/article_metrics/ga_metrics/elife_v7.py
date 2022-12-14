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
        ensure(len(row['dimensionValues']) == 1, "row with multiple dimensionValues found: %s" % row)
        ensure(len(row['metricValues']) == 1, "row with multiple metricValues found: %s" % row)
        path = row['dimensionValues'][0]['value']
        count = row['metricValues'][0]['value']
        regex_obj = re.match(PATH_RE, path.lower())
        ensure(regex_obj, "unhandled path: %s" % row)
        # "/articles/12345/executable" => {'artid': 12345}
        data = regex_obj.groupdict()
        count_type = 'full' # vs 'abstract' or 'digest', from previous eras
        return data['artid'], count_type, int(count)
    except AssertionError as exc:
        LOG.debug("ignoring row, failed expections", exc_info=exc)

def path_counts(path_count_pairs):
    "takes a list of rows from GA4 and groups by msid, returning a list of (msid, count-type, count)"
    path_count_triples = lfilter(None, [path_count(pair) for pair in path_count_pairs])
    return elife_v1.group_results(path_count_triples)

def event_counts_query(table_id, from_date, to_date):
    return {}

def event_counts(row_list):
    pass
