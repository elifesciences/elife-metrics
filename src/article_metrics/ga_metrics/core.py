#!/usr/bin/python
# -*- coding: utf-8 -*-

# Analytics API:
# https://developers.google.com/analytics/devguides/reporting/core/v3/reference

from os.path import join
import os, json, time, random
from datetime import datetime, timedelta
from googleapiclient import errors
from googleapiclient.discovery import build
from oauth2client.client import AccessTokenRefreshError
from oauth2client.service_account import ServiceAccountCredentials
from httplib2 import Http
from .utils import ymd, month_min_max, ensure
from kids.cache import cache
import logging
from django.conf import settings
from . import elife_v1, elife_v2, elife_v3, elife_v4, elife_v5, elife_v6, elife_vX, elife_v7, elife_v8
from . import utils, ga4
from article_metrics.utils import todt_notz, datetime_now

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

# /reviewed-preprints go-live
# lsh@2024-04-05: added the RPP_ADDITION era and adjusted the patterns for subsequent eras.
# we've never had to deal with non-continguous eras before.
RPP_ADDITION = datetime(year=2022, month=10, day=18)
RPP_ADDITION_MONTH = month_min_max(RPP_ADDITION)

# switch from ga3 to ga4
GA4_SWITCH = datetime(year=2023, month=3, day=20)

# switch from custom 'Download' events to the automatically collected ga4 'file_download' events.
GA4_DOWNLOADS_SWITCH = datetime(year=2023, month=6, day=12)

def module_picker(from_date, to_date):
    "returns the module we should be using for scraping this date range."
    daily = from_date == to_date
    monthly = not daily

    if from_date >= GA4_DOWNLOADS_SWITCH:
        return elife_v8

    if from_date >= GA4_SWITCH:
        return elife_v7

    if monthly and \
       (from_date, to_date) == RPP_ADDITION_MONTH:
        # business rule: if the given from-to dates represent a
        # monthly date range and that date range is the same year+month
        # we added /reviewed-preprints, use the vX patterns.
        return elife_vX

    if from_date >= RPP_ADDITION:
        return elife_vX

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
    """returns True if both dates are greater than the date we started collecting on."""
    from_date, to_date = dt_pair
    ensure(isinstance(from_date, datetime), "from_date must be a datetime object, not %r" % (type(from_date),))
    ensure(isinstance(to_date, datetime), "to_date must be a datetime object, not %r" % (type(to_date),))
    ensure(from_date <= to_date, "from_date must be older than or the same as the to_date")
    if from_date < inception:
        LOG.debug("date range invalid, it starts earlier than when we started collecting.")
        return False
    return True

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
    # ga4 queries use `dateRanges.0.startDate`.
    return GA3 if 'start_date' in query_map else GA4

def guess_era_from_response(response):
    # ga4 does not return a 'query' in the response.
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
    if not isinstance(from_date, str):
        # convert date/datetime objects to strings
        from_date, to_date = ymd(from_date), ymd(to_date)

    # different formatting if two different dates are provided
    daily = from_date == to_date
    if daily:
        dt_str = to_date
    else:
        dt_str = "%s_%s" % (from_date, to_date)

    # "output/downloads/2014-04-01.json", "output/downloads/2014-04-01_2014-04-30.json"
    return join(output_dir(), results_type, dt_str + ".json")

def output_path_from_results(response, results_type=None):
    """determines a path where the given response can live, using the
    dates within the response and guessing the request type"""
    assert 'query' in response and 'filters' in response['query'], \
        "can't parse given response: %r" % str(response)
    query = response['query']
    from_date = datetime.strptime(query['start-date'], "%Y-%m-%d")
    to_date = datetime.strptime(query['end-date'], "%Y-%m-%d")
    results_type = results_type or ('downloads' if 'ga:eventLabel' in query['filters'] else 'views')
    path = output_path(results_type, from_date, to_date)

    # do not cache partial results
    cache_threshold = datetime_now() - timedelta(days=3)
    if to_date >= cache_threshold:
        LOG.warning("refusing to cache potentially partial or empty results: %s", path)
        return None

    return path

def write_results(results, path):
    "writes sanitised response from Google as json to the given path"
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        assert os.system("mkdir -p %s" % dirname) == 0, "failed to make output dir %r" % dirname
    LOG.info("writing %r", path)
    with open(path, 'w') as fh:
        json.dump(sanitize_ga_response(results), fh, indent=4, sort_keys=True)

def query_ga_write_results(query, num_attempts=5):
    "convenience. queries GA then writes the results, returning both the original response and the path to results"
    response = query_ga(query, num_attempts)
    path = output_path_from_results(response)
    if path:
        write_results(response, path)
    return response, path


# --- END GA3 LOGIC

def cacheable(to_date_dt):
    "returns `True` if a cache file would be written for `to_date_dt`, or a range ending on this day."
    # GA4 has been observed returning partial results for up to 48 hours in the past.
    # a three day offset here eliminates the current partial day as well as two whole days.
    cache_threshold = datetime_now() - timedelta(days=3)
    return to_date_dt < cache_threshold

def output_path_v2(results_type, from_date_dt, to_date_dt):
    """generates a path for results of the given type.
    same logic as `output_path`, but more strict.
    """
    known_results_types = ['views', 'downloads',
                           'blog-article', 'collection', 'digest', 'event', 'interview', 'labs-post', 'press-package']
    ensure(results_type in known_results_types, "unknown results type %r: %s" % (results_type, ", ".join(known_results_types)))
    ensure(type(from_date_dt) == datetime, "from_date_dt must be a datetime object")
    ensure(type(to_date_dt) == datetime, "to_date_dt must be a datetime object")

    from_date, to_date = ymd(from_date_dt), ymd(to_date_dt)

    # different formatting if two different dates are provided
    daily = from_date == to_date
    if daily:
        dt_str = to_date
    else:
        dt_str = "%s_%s" % (from_date, to_date)

    # ll: output/downloads/2014-04-01.json
    # ll: output/views/2014-01-01_2014-01-31.json
    path = join(settings.GA_OUTPUT_SUBDIR, results_type, dt_str + ".json")

    # do not cache partial results
    if not cacheable(to_date_dt):
        LOG.warning("cache file will not be written: %s", path)
        return None

    return path

def load_cache(results_type, from_date, to_date, cached, only_cached):
    """returns the contents of the cached data for the given `results_type` on the given date range.
    returns an empty dict when `cached` is `True`, `only_cached` is `True` but no cached file exists.
    returns `None` when `cached` is `False`.
    returns `None` when given date range is not cachable."""
    if cached and cacheable(to_date):
        path = output_path_v2(results_type, from_date, to_date)
        has_cache = path and os.path.exists(path)
        if has_cache:
            with open(path, 'r') as fh:
                return json.load(fh)
        elif only_cached:
            # no cache exists and we've been told to only use cache.
            return {}

def write_results_v2(results, path):
    """writes `results` as json to the given `path`.
    like v1, but expects output directory to exist and will not create it if it doesn't."""
    dirname = os.path.dirname(path)
    ensure(os.path.exists(dirname), "output directory does not exist: %s" % path)
    LOG.debug("writing %r", path)
    json.dump(results, open(path, 'w'), indent=4, sort_keys=True)

def query_ga_write_results_v2(query_map, from_date_dt, to_date_dt, results_type, **kwargs):
    if guess_era_from_query(query_map) == GA3:
        return query_ga_write_results(query_map, **kwargs)

    results = ga4.query_ga(query_map, **kwargs)
    query_start = todt_notz(query_map['dateRanges'][0]['startDate'])
    query_end = todt_notz(query_map['dateRanges'][0]['endDate'])
    path = output_path_v2(results_type, query_start, query_end)
    if path:
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

    elife_module = module_picker(from_date, to_date)

    raw_data = load_cache('views', from_date, to_date, cached, only_cached)
    if raw_data is None:
        # talk to google
        query_map = elife_module.path_counts_query(table_id, from_date, to_date)
        raw_data, _ = query_ga_write_results_v2(query_map, from_date, to_date, 'views')

    return elife_module.path_counts(raw_data.get('rows', []))

def article_downloads(table_id, from_date, to_date, cached=False, only_cached=False):
    "returns article download data either from the cache or from talking to google"
    if not valid_downloads_dt_pair((from_date, to_date)):
        LOG.warning("given date range %r for downloads is older than known inception %r, skipping", (ymd(from_date), ymd(to_date)), DOWNLOADS_INCEPTION)
        return {}

    elife_module = module_picker(from_date, to_date)

    raw_data = load_cache('downloads', from_date, to_date, cached, only_cached)
    if raw_data is None:
        # talk to google
        query_map = elife_module.event_counts_query(table_id, from_date, to_date)
        raw_data, _ = query_ga_write_results_v2(query_map, from_date, to_date, 'downloads')

    return elife_module.event_counts(raw_data.get('rows', []))

def article_metrics(table_id, from_date, to_date, cached=False, only_cached=False):
    "returns a dictionary of article metrics, combining both article views and pdf downloads"
    return {
        'views': article_views(table_id, from_date, to_date, cached, only_cached),
        'downloads': article_downloads(table_id, from_date, to_date, cached, only_cached),
    }

def metrics_for_range(table_id, dt_range_list, cached=False, only_cached=False):
    """query each `(from-date, to-date)` pair in `dt_range_list`.
    returns a map of `{(from-date, to-date): {'views': {...}, 'downloads': {...}}`"""
    results = {}
    for from_date, to_date in dt_range_list:
        res = article_metrics(table_id, from_date, to_date, cached, only_cached)
        results[(ymd(from_date), ymd(to_date))] = res
    return results

def daily_metrics_between(table_id, from_date, to_date, cached=True, only_cached=False):
    "does a DAILY query between two dates, NOT a single query within a date range."
    date_range = utils.dt_range(from_date, to_date)
    return metrics_for_range(table_id, date_range, cached, only_cached)

def monthly_metrics_between(table_id, from_date, to_date, cached=True, only_cached=False):
    date_range = utils.dt_month_range(from_date, to_date)
    return metrics_for_range(table_id, date_range, cached, only_cached)
