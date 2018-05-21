"""
elife_v4, the switch to 'elife 2.0'

this is/was the long-awaited for overhaul of the website to a microservices platform.

the urls become greatly simplified. no more volumes, no content types, no abstracts ...

"""

# we can reuse these functions
from . import elife_v1
# these seemingly unused imports are actually used
from .elife_v1 import group_results
from article_metrics.utils import lfilter
import re
import logging

LOG = logging.getLogger(__name__)

# has downloads event counting changed?
event_counts_query = elife_v1.event_counts_query
event_counts = elife_v1.event_counts

# views counting

def path_counts_query(table_id, from_date, to_date):
    # use the v1 query as a template
    new_query = elife_v1.path_counts_query(table_id, from_date, to_date)
    new_query['filters'] = r'ga:pagePath=~^/articles/[0-9]+$' # note: GA doesn't support {n,m} syntax. you're not crazy
    return new_query

REGEX = r"/articles/(?P<artid>\d{1,5})$" # python does support it though, so we can filter bad eggs in post
PATH_RE = re.compile(REGEX, re.IGNORECASE)

def path_count(pair):
    "handles a single pair of (path, count). emits a triple of (art-id, art-type, count)"
    path, count = pair
    # path ll: /articles/12345
    bits = re.match(PATH_RE, path.lower())
    if not bits:
        LOG.warn("skpping unhandled path %s", pair)
        return
    data = bits.groupdict()
    return data['artid'], 'full', int(count)

def path_counts(path_count_pairs):
    return group_results(lfilter(None, map(path_count, path_count_pairs)))
