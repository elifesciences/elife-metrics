from kids.cache import cache
import time, random
import googleapiclient, oauth2client
import googleapiclient.discovery
import oauth2client.service_account
import httplib2
import logging
from django.conf import settings
from ..utils import ensure, datetime_now
from article_metrics.utils import todt_notz
from datetime import timedelta

LOG = logging.getLogger(__name__)

# Analytics API:
# https://developers.google.com/analytics/devguides/reporting/data/v1/rest

@cache
def ga_service():
    service_name = 'analyticsdata'
    service_version = 'v1beta'
    scope = 'https://www.googleapis.com/auth/analytics.readonly'
    credentials = oauth2client.service_account.ServiceAccountCredentials.from_json_keyfile_name(settings.GA_SECRETS_LOCATION, scopes=[scope])
    http = httplib2.Http()
    credentials.authorize(http) # does this 'put' back into the credentials file??
    # `cache_discovery=False`:
    # - https://github.com/googleapis/google-api-python-client/issues/299
    # - https://github.com/googleapis/google-api-python-client/issues/345
    service = googleapiclient.discovery.build(service_name, service_version, http=http, cache_discovery=False)
    return service

# pylint: disable=E1101
def _query_ga(query_map, num_attempts=5):
    """talks to GA, executing the given `query_map`.
    applies exponential back-off if rate limited or when service is unavailable."""

    ensure(isinstance(query_map['dateRanges'][0]['startDate'], str), 'startDate must be a string: %s' % query_map)
    ensure(isinstance(query_map['dateRanges'][0]['endDate'], str), 'endDate must be a string')

    # lsh@2023-07-12: hard fail if we somehow managed to generate a query that might generate partial data
    now = datetime_now()
    yesterday = now - timedelta(days=1)
    end_date = todt_notz(query_map['dateRanges'][0]['endDate'])
    ensure(end_date < now, "refusing to query GA4, query `end_date` will generate partial/empty results")
    ensure(end_date < yesterday, "refusing to query GA4, query `end_date` will generate partial/empty results")

    property_id = 'properties/' + settings.GA4_TABLE_ID
    query = ga_service().properties().runReport(property=property_id, body=query_map)

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

        except googleapiclient.errors.HttpError as e:
            LOG.debug("HttpError ... can we recover?")

            status_code = e.resp.status

            if status_code == 403:
                # apply exponential backoff.
                ms_dither = random.randint(0, 1000) / 1000
                seconds = (2 ** n) # 2**0 => 1, 2**1 => 2, 2**2 => 4, 2**3 => 8
                backoff = seconds + ms_dither # 8.607
                LOG.info("403 rate limited. backoff is %ss", backoff)
                time.sleep(backoff)

            if status_code == 503:
                # apply exponential backoff.
                ms_dither = random.randint(0, 1000) / 1000
                seconds = (2 ** n)
                # wait even longer
                seconds = seconds * 2
                backoff = seconds + ms_dither
                LOG.warning("503 service unavailable. backoff is %ss", backoff)
                time.sleep(backoff)

            else:
                # some other sort of HttpError, re-raise
                LOG.exception("unhandled exception querying GA")
                raise

        except oauth2client.client.AccessTokenRefreshError:
            # Handle Auth errors.
            LOG.error('The credentials have been revoked or expired, please re-run the application to re-authorize')
            raise

    raise AssertionError("Failed to execute query after %s attempts" % num_attempts)

def query_ga(query, **kwargs):
    """performs given `query` and fetches any further pages.
    results are concatenated and returned as part of the last response dict as `rows`."""

    results_pp = query['limit'] = 10000 # 100k max
    query['offset'] = 0

    page, results = 1, []
    while True:
        LOG.info("requesting page %s for query %s" % (page, query))  # ['filters']))
        response = _query_ga(query, **kwargs)
        if not response.get('rows'):
            break # empty response
        results.extend(response['rows'])
        if (results_pp * page) >= response['rowCount']:
            break # no more pages to fetch
        query['offset'] += results_pp # 0, 1000, 2000, 3000, etc
        page += 1

    # use the last response given but with all of the results
    response['rows'] = results
    response['-total-pages'] = page
    return response
