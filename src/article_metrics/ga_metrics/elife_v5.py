"elife_v5, the addition of /executable paths"

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
    # use the v1 query as a template
    new_query = elife_v1.path_counts_query(table_id, from_date, to_date)
    new_query['filters'] = ','.join([
        # ga:pagePath=~^/articles/50101$
        r'ga:pagePath=~^/articles/[0-9]+$', # note: GA doesn't support {n,m} syntax ...

        # ga:pagePath=~^/articles/50101/executable$
        r'ga:pagePath=~^/articles/[0-9]+/executable$',
    ])
    return new_query

# ...python *does* support {n,m} though, so we can filter bad article IDs in post
# parse the article ID from a path that may include an optional '/executable'
REGEX = r"/articles/(?P<artid>\d{1,5})(/executable)?$"
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
    """takes raw path data from GA and groups by article, returning a
    list of (artid, count-type, count)"""
    path_count_triples = lfilter(None, [path_count(pair) for pair in path_count_pairs])
    return elife_v1.group_results(path_count_triples)
