import requests
import logging
from django.conf import settings
from article_metrics import models, handler, utils
from article_metrics.utils import first, flatten, simple_rate_limiter, lfilter, isint, ParseError, ensure

LOG = logging.getLogger(__name__)

URL = "https://api.elsevier.com/content/search/scopus"

MAX_PER_SECOND = 3

@simple_rate_limiter(MAX_PER_SECOND) # no more than this per second
def fetch_page(api_key, doi_prefix, page=0, per_page=25):
    "fetches a page of scopus search results"
    params = {
        'query': 'DOI("%s/*")' % doi_prefix,
        # 'query': 'DOI("10.7554/eLife.00471")',
        # 'field': 'citedby-count', # not too useful unless we combine it with other fields
        # 'view': 'COMPLETE' # verboten
        'start': page, # a 400 is thrown when we page out
        'count': per_page,
        'sort': 'citedby-count',
    }
    LOG.debug('calling scopus with params: %s', params)
    headers = {
        'Accept': 'application/json',
        'X-ELS-APIKey': api_key,
        'User-Agent': settings.USER_AGENT,
    }
    # https://dev.elsevier.com/tecdoc_cited_by_in_scopus.html
    # http://api.elsevier.com/documentation/SCOPUSSearchAPI.wadl
    return handler.requests_get(URL, params=params, headers=headers)

def search(api_key=settings.SCOPUS_KEY, doi_prefix=settings.DOI_PREFIX):
    """searches scopus, returning a generator that will iterate through each page
    of results until all pages have been consumed.
    results are cached and expire daily"""

    page = 0
    per_page = 25 # max per page

    data = fetch_page(api_key, doi_prefix, page=page, per_page=per_page).json()

    yield data['search-results']

    # I think this is 'total pages'
    # you can certainly query far far beyond 'totalResults / per_page'
    total_pages = int(data['search-results']['opensearch:totalResults'])

    # I think we're capped at 10k/day ? can't find their docs on this
    # eLife tends to hit 0 citations at about the 2.5k mark
    max_pages = 5000

    # figure out where to stop
    end_page = max_pages if total_pages > max_pages else total_pages

    try:
        for page in range(page + 1, end_page):
            try:
                data = fetch_page(api_key, doi_prefix, page=page, per_page=per_page).json()
                yield data['search-results']

                # find the first entry in the search results with a 'citedby-count'.
                # this is typically the first but we have results where it's missing
                fltrfn = lambda d: 'citedby-count' in d and isint(d['citedby-count'])
                entry = first(lfilter(fltrfn, data['search-results']['entry']))

                # exit early if we start hitting 0 results
                if entry and int(entry['citedby-count']) == 0:
                    raise GeneratorExit("no more articles with citations")

                # every ten pages print out our progress
                if page % 10 == 0:
                    LOG.info("page %s of %s, last citation count: %s" % (page, end_page, entry['citedby-count']))

            except requests.HTTPError as err:
                raise GeneratorExit(str(err))

    except GeneratorExit:
        return

@handler.capture_parse_error
def parse_entry(entry):
    "parses a single search result from scopus"
    try:
        citedby_link = first(lfilter(lambda d: d["@ref"] == "scopus-citedby", entry['link']))
        ensure('prism:doi' in entry, "entry is missing 'doi'!", ParseError)
        ensure('citedby-count' in entry, "entry is missing 'citedby-count'!", ParseError)
        ensure(isint(entry['citedby-count']), "citedby count isn't an integer", ParseError)

        if isinstance(entry['prism:doi'], list):
            weird_key = "$"
            for struct in entry['prism:doi']:
                doi = struct[weird_key]
                if utils.doi2msid(doi, safe=True, allow_subresource=False):
                    entry['prism:doi'] = doi
                    break

        utils.doi2msid(entry['prism:doi'], allow_subresource=False) # throws AssertionError

        return {
            'doi': entry['prism:doi'],
            'num': int(entry['citedby-count']),
            'source': models.SCOPUS,
            'source_id': citedby_link['@href']
        }

    # errors handled here won't be caught by handler.capture_parse_error

    except AssertionError:
        LOG.warning("discarding scopus citation: failed to parse doi", extra={'response': entry})
        return {'bad': entry}

    except ParseError:
        LOG.warning("discarding scopus citation: failed to parse entry", extra={'response': entry})
        return {'bad': entry}

def parse_result_page(search_result):
    "parses citation counts from a page of search results from scopus"
    return map(parse_entry, search_result['entry'])

def all_entries(search_result_list):
    "returns a list of 'entries', citation information for articles from a *list* of search result pages"
    return flatten(map(parse_result_page, search_result_list))

# ---

def all_todays_entries():
    "convenience"
    return all_entries(search())
