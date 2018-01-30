import requests
import logging
from django.conf import settings
from metrics import models, handler
from metrics.utils import first, flatten, simple_rate_limiter, lmap

LOG = logging.getLogger(__name__)

URL = "https://api.elsevier.com/content/search/scopus"

MAX_PER_SECOND = 3

@simple_rate_limiter(MAX_PER_SECOND) # no more than this per second
def fetch_page(api_key, doi_prefix, page=0, per_page=25):
    "fetches a page of scopus search results"
    params = {
        'query': 'DOI("%s/*")' % doi_prefix,
        #'query': 'DOI("10.7554/eLife.00471")',
        #'field': 'citedby-count', # not too useful unless we combine it with other fields
        #'view': 'COMPLETE' # verboten
        'start': page, # a 400 is thrown when we page out
        'count': per_page,
        'sort': 'citedby-count',
    }
    LOG.info('calling scopus with params: %s', params)
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
    try:
        for page in range(page + 1, total_pages):
            LOG.debug("page %r", page)

            try:
                if page == max_pages:
                    raise GeneratorExit("hit max pages (%s)" % max_pages)

                data = fetch_page(api_key, doi_prefix, page=page, per_page=per_page).json()
                yield data['search-results']

                # exit early if we start hitting 0 results
                fentry = data['search-results']['entry'][0]['citedby-count']
                if int(fentry) == 0:
                    raise GeneratorExit("no more articles with citations")

            except requests.HTTPError as err:
                raise GeneratorExit(str(err))

    except GeneratorExit:
        return

@handler.capture_parse_error
def parse_entry(entry):
    "parses a single search result from scopus"
    citedby_link = first(filter(lambda d: d["@ref"] == "scopus-citedby", entry['link']))
    return {
        'doi': entry['prism:doi'],
        'num': int(entry['citedby-count']),
        'source': models.SCOPUS,
        'source_id': citedby_link['@href']
    }

def parse_results(search_result):
    "parses citation counts from a page of search results from scopus"
    return lmap(parse_entry, search_result['entry'])

def all_entries(search_result_list):
    "returns a list of 'entries', citation information for articles from a list of search result pages"
    return flatten([parse_entry(result['entry']) for result in search_result_list])

def is_abstract(entry):
    # ll 10.7554/eLife.22757.001
    return len(entry['doi'].split('.')) == 4

def not_abstract(entry):
    return not is_abstract(entry)

#
#
#

def all_todays_entries():
    "convenience"
    # return filter(not_abstract, all_entries(list(search())))
    return all_entries(list(search()))
