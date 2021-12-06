"elife_v6, includes urls with certain parameters"

from . import elife_v1
from article_metrics.utils import lfilter
import re
import logging

LOG = logging.getLogger(__name__)

event_counts_query = elife_v1.event_counts_query
event_counts = elife_v1.event_counts

# views counting

def path_counts_query(table_id, from_date, to_date):
    "returns a query specific to this era that we can send to Google Analytics"
    new_query = elife_v1.path_counts_query(table_id, from_date, to_date)
    explanation = (
        # non-regex GA prefix where '=~' means 'match regex'
        "ga:pagePath=~"
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
    ga_filter = "ga:pagePath=~^/articles/[0-9]+(/executable)?((\\?|&){1}.*?(twclid|utm_campaign|utm_source=content_alert)+.*?)?$"
    assert ga_filter == explanation, "explanation of filter differs from the actual filter."

    new_query['filters'] = ga_filter
    return new_query

# ...python *does* support {n,m} though, so we can filter bad article IDs in post
# lsh@2021-11-30: still true.
# parse the article ID from a path that may include an optional '/executable'.
REGEX = r"/articles/(?P<artid>\d{1,5})"
PATH_RE = re.compile(REGEX, re.IGNORECASE)

def path_count(pair):
    "given a pair of (path, count), returns a triple of (art-id, art-type, count)"
    path, count = pair
    regex_obj = re.match(PATH_RE, path.lower())
    if not regex_obj:
        LOG.debug("skpping unhandled path %s", pair)
        return
    # "/articles/12345/executable" => {'artid': 12345}
    data = regex_obj.groupdict()
    count_type = 'full' # vs 'abstract' or 'digest' from previous eras
    return data['artid'], count_type, int(count)

def path_counts(path_count_pairs):
    """takes raw path data from GA and groups by msid, returning a
    list of (msid, count-type, count)"""
    path_count_triples = lfilter(None, [path_count(pair) for pair in path_count_pairs])
    return elife_v1.group_results(path_count_triples)
