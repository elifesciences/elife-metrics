#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
elife_v3, the switch to versionless urls

essentially the same as elife_v2 BUT the version suffix is now optional.

"""

# we can reuse these functions
import elife_v1
# these seemingly unused imports are actually used
from .elife_v1 import group_results
import re
import logging

logging.basicConfig()
LOG = logging.getLogger(__name__)
LOG.level = logging.INFO

event_counts_query = elife_v1.event_counts_query
event_counts = elife_v1.event_counts

def path_counts_query(table_id, from_date, to_date):
    "returns the raw GA results for PDF downloads between the two given dates"
    new_query = elife_v1.path_counts_query(table_id, from_date, to_date)

    suffix_list = [
        'v[0-9]{1}', # 'v1', 'v2', 'v3' ... 'v9'
        'v[0-9]{1}/abstract', # 'v1/abstract'
        'v[0-9]{1}/abstract[0-9]{1}', # 'v1/abstract2' (digest)
    ]

    suffix_str = '|'.join(suffix_list)

    new_query.update({
        'filters': ','.join([
            r'ga:pagePath=~^/content/[0-9]{1}/e[0-9]{5}$',
            r'ga:pagePath=~^/content/[0-9]{1}/e[0-9]{5}(%s)$' % suffix_str,
        ]),
    })
    return new_query

REGEX = r"/content/(?P<volume>\d{1})/(?P<artid>e\d+)(v(?P<version>\d{1})(?P<type>/abstract|/abstract2)*)?$"
PATH_RE = re.compile(REGEX, re.IGNORECASE)

TYPE_MAP = {
    None: 'full',
    '/abstract': 'abstract',
    '/abstract2': 'digest'
}

def path_count(pair):
    "handles a single pair of (path, count). emits a triple of (art-id, art-type, count)"
    path, count = pair
    # path will always be something similar to: /content/4/e10719v1
    bits = re.search(PATH_RE, path.lower())
    if not bits:
        LOG.warn("skpping unhandled path %s", pair)
        return
    data = bits.groupdict()
    return data['artid'], TYPE_MAP[data['type']], int(count)

def path_counts(path_count_pairs):
    return group_results(filter(None, map(path_count, path_count_pairs)))
