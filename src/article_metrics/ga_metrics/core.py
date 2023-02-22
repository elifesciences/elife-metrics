#!/usr/bin/python
# -*- coding: utf-8 -*-

# Analytics API:
# https://developers.google.com/analytics/devguides/reporting/core/v3/reference

from os.path import join
import os, json, time, random
from datetime import datetime
from googleapiclient import errors
from googleapiclient.discovery import build
from oauth2client.client import AccessTokenRefreshError
from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
from .utils import ymd, month_min_max, d2dt, ensure
from kids.cache import cache
import logging
from django.conf import settings
from . import elife_v1, elife_v2, elife_v3, elife_v4, elife_v5, elife_v6, elife_v7
from . import utils, ga4
from article_metrics.utils import lfilter

LOG = logging.getLogger(__name__)

MAX_GA_RESULTS = 10000
GA3, GA4 = 'ga3', 'ga4'

# lsh@2021-12: test logic doesn't belong here. replace with a mock during testing
def output_dir():
    root = os.path.dirname(os.path.dirname(__file__))
    if os.environ.get('TESTING'):
        root = os.getenv('TEST_OUTPUT_DIR')
    return join(root, settings.GA_OUTPUT_SUBDIR)

VIEWS_INCEPTION = datetime(year=2014, month=3, day=12)
DOWNLOADS_INCEPTION = datetime(year=2015, month=2, day=13)

# when we switched away from HW
SITE_SWITCH = datetime(year=2016, month=2, day=9)

# when we were told to use versionless urls for latest article version
# https://github.com/elifesciences/elife-website/commit/446408019f7ec999adc6c9a80e8fa28966a42304
VERSIONLESS_URLS = datetime(year=2016, month=5, day=5)
VERSIONLESS_URLS_MONTH = month_min_max(VERSIONLESS_URLS)

# when we first started using 2.0 urls
SITE_SWITCH_v2 = datetime(year=2017, month=6, day=1)

# when we added /executable
RDS_ADDITION = datetime(year=2020, month=2, day=21)

# whitelisted urlparams
URL_PARAMS = datetime(year=2021, month=11, day=30)

# switch from ga3 to ga4
# todo: fix the module in place during testing, test module_picker separately.
GA4_SWITCH = datetime(year=2023, month=7, day=1)

# todo: compare this to old split logic
def module_picker(from_date, to_date):
    "returns the module we should be using for scraping this date range."
    daily = from_date == to_date
    monthly = not daily

    if from_date >= GA4_SWITCH:
        return elife_v7

    if from_date > URL_PARAMS:
        return elife_v6

    if from_date >= RDS_ADDITION:
        return elife_v5

    if from_date >= SITE_SWITCH_v2:
        return elife_v4

    if monthly and \
       (from_date, to_date) == VERSIONLESS_URLS_MONTH:
        # business rule: if the given from-to dates represent a
        # monthly date range and that date range is the same year+month
        # we switched to versionless urls, use the v3 patterns.
        return elife_v3

    # if the site switched to versionless urls before our date range, use v3
    if from_date > VERSIONLESS_URLS:
        return elife_v3

    if from_date > SITE_SWITCH:
        return elife_v2

    # TODO, WARN: partial month logic here
    # if the site switch happened between our two dates, use new.
    # if monthly, this means we lose 9 days of stats
    if monthly and \
       SITE_SWITCH > from_date and SITE_SWITCH < to_date:
        return elife_v2

    return elife_v1


#
# utils
#

def valid_dt_pair(dt_pair, inception):
    "returns true if both dates are greater than the date we started collecting on"
    from_date, to_date = dt_pair
    ensure(isinstance(from_date, datetime), "from_date must be a datetime object, not %r" % (type(from_date),))
    ensure(isinstance(to_date, datetime), "to_date must be a datetime object, not %r" % (type(to_date),))
    return from_date >= inception and to_date >= inception

def valid_view_dt_pair(dt_pair):
    "returns true if both dates are greater than the date we started collecting on"
    return valid_dt_pair(dt_pair, VIEWS_INCEPTION)

def valid_downloads_dt_pair(dt_pair):
    "returns true if both dates are greater than the date we started collecting on"
    return valid_dt_pair(dt_pair, DOWNLOADS_INCEPTION)

SANITISE_THESE = ['profileInfo', 'id', 'selfLink']

def sanitize_ga_response(ga_response):
    """The GA responses contain no sensitive information, however it does
    have a collection of identifiers I'd feel happier if the world didn't
    have easy access to."""
    for key in SANITISE_THESE:
        if key in ga_response:
            del ga_response[key]
    if 'ids' in ga_response['query']:
        del ga_response['query']['ids']
    return ga_response

@cache
def ga_service():
    service_name = 'analytics'
    settings_file = settings.GA_SECRETS_LOCATION
    scope = 'https://www.googleapis.com/auth/analytics.readonly'
    credentials = ServiceAccountCredentials.from_json_keyfile_name(settings_file, scopes=[scope])
    http = Http()
    credentials.authorize(http) # does this 'put' back into the credentials file??
    # `cache_discovery=False`:
    # - https://github.com/googleapis/google-api-python-client/issues/299
    # - https://github.com/googleapis/google-api-python-client/issues/345
    service = build(service_name, 'v3', http=http, cache_discovery=False)
    return service

def guess_era_from_query(query_map):
    return GA3 if 'start_date' in query_map else GA4

def guess_era_from_response(response):
    return GA3 if 'query' in response else GA4

# --- GA3 logic

# pylint: disable=E1101
def _query_ga(query_map, num_attempts=5):
    "talks to google with the given query, applying exponential back-off if rate limited"

    # build the query
    if isinstance(query_map, dict):

        # clean up query, dates to strings, etc
        query_map['start_date'] = ymd(query_map['start_date'])
        query_map['end_date'] = ymd(query_map['end_date'])

        if not query_map['ids'].startswith('ga:'):
            query_map['ids'] = 'ga:%s' % query_map['ids']

        query = ga_service().data().ga().get(**query_map)
    else:
        # a regular query object can be passed in
        query = query_map

    # execute it
    for n in range(0, num_attempts):
        try:
            if n > 1:
                LOG.info("query attempt %r" % (n + 1))
            else:
                LOG.info("querying ...")
            return query.execute()

        except TypeError as error:
            # Handle errors in constructing a query.
            LOG.exception('There was an error in constructing your query : %s', error)
            raise

        except errors.HttpError as e:
            LOG.warning("HttpError ... can we recover?")

            status_code = e.resp.status

            if status_code in [403, 503]:

                # apply exponential backoff.
                val = (2 ** n) + random.randint(0, 1000) / 1000
                if status_code == 503:
                    # wait even longer
                    val = val * 2

                LOG.info("rate limited. backing off %r", val)
                time.sleep(val)

            else:
                # some other sort of HttpError, re-raise
                LOG.exception("unhandled exception!")
                raise

        except AccessTokenRefreshError:
            # Handle Auth errors.
            LOG.exception('The credentials have been revoked or expired, please re-run '
                          'the application to re-authorize')
            raise

    raise AssertionError("Failed to execute query after %s attempts" % num_attempts)

# copied from non-article metrics logic.py
def query_ga(query, num_attempts=5):
    """performs given query and fetches any further pages.
    concatenated results are returned in the response dict as `rows`."""

    results_pp = query.get('max_results', MAX_GA_RESULTS)
    query['max_results'] = results_pp
    query['start_index'] = 1

    page, results = 1, []
    while True:
        LOG.info("requesting page %s for query %s" % (page, query['filters']))
        response = _query_ga(query, num_attempts)
        results.extend(response.get('rows') or [])
        if (results_pp * page) >= response['totalResults']:
            break # no more pages to fetch
        query['start_index'] += results_pp # 1, 2001, 4001, etc
        page += 1

    # use the last response given but with all of the results
    response['rows'] = results
    response['totalPages'] = page

    return response

def output_path(results_type, from_date, to_date):
    "generates a path for results of the given type"
    # `output_path` now used by non-article metrics app to create a cache path for *their* ga responses
    #assert results_type in ['views', 'downloads'], "results type must be either 'views' or 'downloads', not %r" % results_type
    if isinstance(from_date, str): # given strings
        #from_date_dt = datetime.strptime(from_date, "%Y-%m-%d")
        to_date_dt = datetime.strptime(to_date, "%Y-%m-%d")
    else: # given date/datetime objects
        to_date_dt = d2dt(to_date)
        from_date, to_date = ymd(from_date), ymd(to_date)

    now, now_dt = ymd(datetime.now()), datetime.now()

    # different formatting if two different dates are provided
    if from_date == to_date:
        dt_str = to_date
    else:
        dt_str = "%s_%s" % (from_date, to_date)

    partial = ""
    if to_date == now or to_date_dt >= now_dt:
        # anything gathered today or for the future (month ranges)
        # will only ever be partial. when run again on a future day
        # there will be cache miss and the full results downloaded
        partial = ".partial"

    # ll: output/downloads/2014-04-01.json
    # ll: output/views/2014-01-01_2014-01-31.json.partial
    return join(output_dir(), results_type, dt_str + ".json" + partial)

def output_path_from_results(response, results_type=None):
    """determines a path where the given response can live, using the
    dates within the response and guessing the request type"""
    assert 'query' in response and 'filters' in response['query'], \
        "can't parse given response: %r" % str(response)
    query = response['query']
    from_date = datetime.strptime(query['start-date'], "%Y-%m-%d")
    to_date = datetime.strptime(query['end-date'], "%Y-%m-%d")
    results_type = results_type or ('downloads' if 'ga:eventLabel' in query['filters'] else 'views')
    return output_path(results_type, from_date, to_date)

def write_results(results, path):
    "writes sanitised response from Google as json to the given path"
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        assert os.system("mkdir -p %s" % dirname) == 0, "failed to make output dir %r" % dirname
    LOG.info("writing %r", path)
    json.dump(sanitize_ga_response(results), open(path, 'w'), indent=4, sort_keys=True)
    return path

def query_ga_write_results(query, num_attempts=5):
    "convenience. queries GA then writes the results, returning both the original response and the path to results"
    response = query_ga(query, num_attempts)
    path = output_path_from_results(response)
    return response, write_results(response, path)


# --- END GA3 LOGIC

def output_path_v2(results_type, from_date_dt, to_date_dt):
    """generates a path for results of the given type.
    same logic as `output_path`, but more strict.
    """
    known_results_types = ['views', 'downloads',
                           'blog-article', 'collection', 'digest', 'event', 'interview', 'labs-post', 'press-package']
    ensure(results_type in known_results_types, "unknown results type %r: %s" % (results_type, ", ".join(known_results_types)))
    ensure(isinstance(from_date_dt, datetime), "from_date_dt must be a datetime object")
    ensure(isinstance(to_date_dt, datetime), "to_date_dt must be a datetime object")

    from_date, to_date = ymd(from_date_dt), ymd(to_date_dt)
    now_dt = datetime.now()
    now = ymd(now_dt)

    # different formatting if two different dates are provided
    if from_date == to_date:
        dt_str = to_date
    else:
        dt_str = "%s_%s" % (from_date, to_date)

    partial = ""
    if to_date == now or to_date_dt >= now_dt:
        # anything gathered today or for the future (month ranges)
        # will only ever be partial. when run again on a future day
        # there will be cache miss and the full results downloaded
        partial = ".partial"

    # ll: output/downloads/2014-04-01.json
    # ll: output/views/2014-01-01_2014-01-31.json.partial
    return join(settings.GA_OUTPUT_SUBDIR, results_type, dt_str + ".json" + partial)

def write_results_v2(results, path):
    "writes `results` as json to the given `path`"
    dirname = os.path.dirname(path)
    ensure(os.path.exists(dirname), "output directory does not exist: %s" % path)
    LOG.info("writing %r", path)
    json.dump(results, open(path, 'w'), indent=4, sort_keys=True)

def query_ga_write_results_v2(query_map, from_date_dt, to_date_dt, results_type, **kwargs):
    if guess_era_from_query(query_map) == GA3:
        return query_ga_write_results(query_map, **kwargs)

    results = ga4.query_ga(query_map, **kwargs)
    path = output_path_v2(results_type, from_date_dt, to_date_dt)
    write_results_v2(results, path)
    return results, path

#
#
#

def article_views(table_id, from_date, to_date, cached=False, only_cached=False):
    "returns article view data either from the cache or from talking to google"
    if not valid_view_dt_pair((from_date, to_date)):
        LOG.warning("given date range %r for views is older than known inception %r, skipping", (ymd(from_date), ymd(to_date)), VIEWS_INCEPTION)
        return {}

    path = output_path_v2('views', from_date, to_date)
    module = module_picker(from_date, to_date)
    if cached and os.path.exists(path):
        raw_data = json.load(open(path, 'r'))
    elif only_cached:
        # no cache exists and we've been told to only use cache.
        # no results found.
        raw_data = {}
    else:
        # talk to google
        query_map = module.path_counts_query(table_id, from_date, to_date)
        raw_data, actual_path = query_ga_write_results_v2(query_map, 'views', from_date, to_date)
        assert path == actual_path, "the expected output path (%s) doesn't match the path actually written to (%s)" % (path, actual_path)
    return module.path_counts(raw_data.get('rows', []))

def article_downloads(table_id, from_date, to_date, cached=False, only_cached=False):
    "returns article download data either from the cache or from talking to google"
    if not valid_downloads_dt_pair((from_date, to_date)):
        LOG.warning("given date range %r for downloads is older than known inception %r, skipping", (ymd(from_date), ymd(to_date)), DOWNLOADS_INCEPTION)
        return {}

    path = output_path_v2('downloads', from_date, to_date)
    module = module_picker(from_date, to_date)
    if cached and os.path.exists(path):
        raw_data = json.load(open(path, 'r'))
    elif only_cached:
        # no cache exists and we've been told to only use cache.
        # no results found.
        raw_data = {}
    else:
        # talk to google
        query_map = module.event_counts_query(table_id, from_date, to_date)
        raw_data, actual_path = query_ga_write_results_v2(query_map, 'downloads', from_date, to_date)
        assert path == actual_path, "the expected output path (%s) doesn't match the path actually written to (%s)" % (path, actual_path)
    return module.event_counts(raw_data.get('rows', []))

def article_metrics(table_id, from_date, to_date, cached=False, only_cached=False):
    "returns a dictionary of article metrics, combining both article views and pdf downloads"
    views = article_views(table_id, from_date, to_date, cached, only_cached)
    downloads = article_downloads(table_id, from_date, to_date, cached, only_cached)

    download_dois = set(downloads.keys())
    views_dois = set(views.keys())
    sset = download_dois - views_dois
    if sset:
        msg = "downloads with no corresponding page view: %r"
        LOG.warning(msg, {missing_doi: downloads[missing_doi] for missing_doi in list(sset)})

    # keep the two separate until we introduce POAs? or just always
    return {'views': views, 'downloads': downloads}


# --- bulk.py, bulk requests to GA
# --- used to be a separate module, tacked on here so I don't go cross-eyed switching panes


def generate_queries(table_id, query_func_name, datetime_list, use_cached=False, use_only_cached=False):
    "returns a list of queries to be executed by google"
    assert isinstance(query_func_name, str), "query func name must be a string"
    query_list = []
    for start_date, end_date in datetime_list:
        module = module_picker(start_date, end_date)
        query_func = getattr(module, query_func_name)
        query_type = 'views' if query_func_name == 'path_counts_query' else 'downloads'

        path = output_path(query_type, start_date, end_date)

        LOG.debug("looking for metrics here: %s", path)
        if use_cached:
            if os.path.exists(path):
                LOG.debug("we have %r results for %r to %r already", query_type, ymd(start_date), ymd(end_date))
                continue
            else:
                LOG.info("no cache file for %r results for %r to %r", query_type, ymd(start_date), ymd(end_date))
        else:
            LOG.debug("couldn't find file %r", path)

        if use_only_cached:
            LOG.info("skipping google query, using only cache files")
            continue

        q = query_func(table_id, start_date, end_date)
        query_list.append(q)

    if use_only_cached:
        # code problem
        assert query_list == [], "use_only_cached==True but we're accumulating queries somehow"

    return query_list

def bulk_query(query_list):
    """executes a list of queries for their side effects (caching).
    results do not accumulate in memory, returns nothing."""
    for query in query_list:
        query_ga_write_results(query) # todo: not v2

def metrics_for_range(table_id, dt_range_list, use_cached=False, use_only_cached=False):
    """query each `(from-date, to-date)` pair in `dt_range_list`.
    returns a map of `{(from-date, to-date): {'views': {...}, 'downloads': {...}}`"""
    results = {}
    for from_date, to_date in dt_range_list:
        res = article_metrics(table_id, from_date, to_date, use_cached, use_only_cached)
        results[(ymd(from_date), ymd(to_date))] = res
    return results

def daily_metrics_between(table_id, from_date, to_date, use_cached=True, use_only_cached=False):
    "does a DAILY query between two dates, NOT a single query within a date range."
    # lsh@2022-12-14: while this per-day querying was perhaps an inefficient decision in UA (GA3),
    # it's a good choice in GA4 as it avoids `(other)` row aggregation. At least for now.

    date_list = utils.dt_range(from_date, to_date)
    query_list = []

    views_dt_range = lfilter(valid_view_dt_pair, date_list)
    query_list.extend(generate_queries(table_id,
                                       'path_counts_query',
                                       views_dt_range,
                                       use_cached, use_only_cached))

    pdf_dt_range = lfilter(valid_downloads_dt_pair, date_list)
    query_list.extend(generate_queries(table_id,
                                       'event_counts_query',
                                       pdf_dt_range,
                                       use_cached, use_only_cached))

    bulk_query(query_list)

    # everything should be cached by now
    use_cached = True # DELIBERATE
    return metrics_for_range(table_id, views_dt_range, use_cached, use_only_cached)

def monthly_metrics_between(table_id, from_date, to_date, use_cached=True, use_only_cached=False):
    date_list = utils.dt_month_range(from_date, to_date)
    views_dt_range = lfilter(valid_view_dt_pair, date_list)
    pdf_dt_range = lfilter(valid_downloads_dt_pair, date_list)

    query_list = []
    query_list.extend(generate_queries(table_id,
                                       'path_counts_query',
                                       views_dt_range,
                                       use_cached, use_only_cached))

    query_list.extend(generate_queries(table_id,
                                       'event_counts_query',
                                       pdf_dt_range,
                                       use_cached, use_only_cached))
    bulk_query(query_list)

    # everything should be cached by now
    use_cached = True # DELIBERATE
    return metrics_for_range(table_id, views_dt_range, use_cached, use_only_cached)
