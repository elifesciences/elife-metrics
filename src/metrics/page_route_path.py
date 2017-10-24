import re
import utils, models
from utils import ensure, first, lfiltermap
from utils import atomic
from ga_metrics import core as ga_core, utils as ga_utils
from datetime import datetime
from django.conf import settings
from collections import Counter
from functools import reduce
import logging

LOG = logging.getLogger(__name__)

def explode_ga_pattern(pattern):
    ga_pattern = "ga:pagePath=~" + pattern

    # TODO: shift this into an 'explode' type function
    if len(pattern) > 128 and '|' in pattern:
        # this regex is too damn long. in some cases we can explode patterns
        # in this case, we're looking for patterns like '/(foo|bar|baz|bup)/' to explode
        regex2 = r"\([()\w|-]+\)" # regex matching regex
        matches = re.finditer(regex2, pattern)
        match = next(matches)
        if not match:
            raise ValueError("failed to reduce size of regular expression. GA will refuse to run this query: %s" % ga_pattern)

        match = match.group()
        subs = match.strip('()').split('|') # explode
        subs = map(lambda sub: ga_pattern.replace(match, sub), subs)

        # final check nothing is huge
        map(lambda sub: ensure(len(sub) <= 128, "GA requires a pattern 128 characters or less: %s" % sub), subs)

        # make a super long expression
        ga_pattern = ",".join(subs)


def ga_regex(pattern):
    return pattern.startswith('ga:pagePath=~')

def insert(page_route):
    ensure(ga_regex(page_route['pattern']), "regular expression doesn't look like something we can give to google.", ValueError)

    page = utils.subdict(page_route, ['name'])
    page, _, _ = utils.create_or_update(models.Page, page, ['name'])

    route = {'page': page, 'pattern': page_route['pattern']}
    route, _, _ = utils.create_or_update(models.Route, route)
    return route


@atomic
def insert_all(page_route_list, dry_run=False):
    return map(first, map(insert, page_route_list))


def norm_path(path):
    "takes a path given to us by GA and normalises it for counting"
    anchor_pos = path.find('#')
    if anchor_pos > -1:
        path = path[:anchor_pos]

    param_pos = path.find('?')
    if param_pos > -1:
        path = path[:param_pos]
    path = path.lower()

    # return None immediately if any unsupported chars are detected
    regex = r"[^\w^\-/\.]+"
    matches = re.finditer(regex, path)
    if next(matches, None):
        return None

    return path

def norm_row(row):
    path, count = row
    path, count = norm_path(path), Counter(count=int(count))
    if not path:
        return None # bad path. will get excluded
    return {
        'path': path,
        'count': count
    }

def update_page_counts(page):
    table_id = ga_utils.norm_table_id(settings.GA_TABLE_ID)
    from_date, to_date = settings.TWOPOINTZERO_START, datetime.now()

    query_map = {
        'ids': table_id,
        'max_results': 10000, # 10,000 is the max GA will ever return
        'start_date': utils.ymd(from_date),
        'end_date': utils.ymd(to_date),
        'metrics': 'ga:sessions', # less flattering, more accurate
        'dimensions': 'ga:pagePath',
        'sort': 'ga:pagePath',
        'filters': page.pattern,
    }
    results = ga_core.query_ga(query_map)

    # post-process the result, do stuff we couldn't do in GA
    results = lfiltermap(norm_row, results.get('rows', []))

    # after normalising the path, we're going to have duplicate paths
    grouped_results = utils.group(results, lambda m: m['path'])

    def aggregate_paths(a, b):
        a.update(b)
        return a

    # these groups of results then need to be aggregated into a single result
    results = map(lambda vals: reduce(aggregate_paths, vals), grouped_results.values())

    def insert_path(row):
        row['count'] = sum(row['count'].values()) # tally the results
        row['page'] = page
        return utils.create_or_update(models.Path, row, ['page', 'path'])

    return map(insert_path, results)

@atomic
def update_all_page_counts(dry_run=False):
    return map(update_page_counts, models.Page.objects.all())
