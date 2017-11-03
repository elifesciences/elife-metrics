from os.path import join
import json
from functools import partial
import re
import utils, models, load_routing as lr
from utils import ensure, first, lfiltermap, todt, ymd
from utils import atomic
from datetime import datetime, timedelta
from ga_metrics import core as ga_core, utils as ga_utils
from django.conf import settings
from collections import Counter
from functools import reduce
import logging
from googleapiclient import errors

LOG = logging.getLogger(__name__)

def save_pages(routing_table):
    return map(lambda pagename: utils.create_or_update(models.Page, {'name': pagename}), routing_table)

def test_route_examples(route):
    "each route contains a number of examples. every example should match against one of the route's frames"
    #ensure(route['examples'], "route missing examples to test")
    #ensure(route['frames'], "route missing frames to test")

    def match(pattern, path):
        return re.match(pattern, path)

    for example_path in route['examples']:
        result = [match(frame['pattern'], example_path) for frame in route['frames']]
        ensure(any(result), "failed to match path %s against any known frame: %s" % (example_path, [f['pattern'] for f in route['frames']]))

def ga_regex(pattern):
    return pattern.startswith('ga:pagePath=~')

def insert(page_route):
    page = utils.subdict(page_route, ['name'])
    return first(utils.create_or_update(models.Page, page, ['name']))

@atomic
def insert_all(page_route_list, dry_run=False):
    return map(insert, page_route_list)

#
#
#

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

def _update_page_counts(page, frame):
    "creates/updates the page counts for a particular "
    table_id = ga_utils.norm_table_id(settings.GA_TABLE_ID)

    earliest = ga_core.VIEWS_INCEPTION
    latest = datetime.now() + timedelta(days=1) # tomorrow

    from_date, to_date = ymd(todt(frame['starts'] or earliest)), ymd(todt(frame['ends'] or latest))
    query_map = {
        'ids': table_id,
        'max_results': 10000, # 10,000 is the max GA will ever return
        'start_date': from_date,
        'end_date': to_date,
        'metrics': 'ga:sessions', # less flattering, more accurate
        'dimensions': 'ga:pagePath',
        'sort': 'ga:pagePath',
        'filters': frame['ga_pattern'],
    }
    try:
        results = ga_core.query_ga(query_map)
        cname = "%s--%s-to-%s" % (page.name, from_date, to_date)
        json.dump(results, open(join(settings.OUTPUT_PATH, 'non-article', cname + ".json"), 'w'), indent=4)

        # post-process the result, do stuff we couldn't do in GA
        return lfiltermap(norm_row, results.get('rows', []))

    except errors.HttpError as e:
        status_code = e.resp.status
        if status_code in [400]:
            payload = utils.lossy_json_dumps(query_map)
            LOG.error("400: we made bad a request to Google Analytics", extra={'request': payload})
            return []


def update_page_counts(route):
    "updates page counts for all of a route's time frames"

    page = models.Page.objects.get(name=route['name'])

    # call update page count for each frame
    per_frame_results = map(partial(_update_page_counts, page), route['frames'])

    # flatten per-frame results into a single list
    results = utils.flatten(per_frame_results)

    # after query each frame and normalising the paths, we're going to have duplicates
    grouped_results = utils.group(results, lambda m: m['path'])

    def aggregate_paths(a, b):
        a['count'] += b['count']
        return a

    # these groups of results then need to be aggregated into a single result
    results = map(lambda vals: reduce(aggregate_paths, vals), grouped_results.values())

    def insert_path(row):
        row['count'] = sum(row['count'].values())
        row['page'] = page
        return utils.create_or_update(models.Path, row, ['page', 'path'])

    return map(insert_path, results)


@atomic
def update_all_page_counts(dry_run=False):
    rtbl = lr.routing_table().values()
    insert_all(rtbl, dry_run)
    #rtblidx = lr.routing_table()
    #rtbl = [rtblidx['inside-elife-article']]
    return map(update_page_counts, rtbl)
