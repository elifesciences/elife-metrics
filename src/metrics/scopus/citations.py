import requests, math
import logging
import requests_cache
from django.conf import settings
from datetime import timedelta
from metrics import models # good idea reaching back?
from metrics.utils import first, flatten

LOG = logging.getLogger(__name__)

requests_cache.install_cache(**{
    'cache_name': settings.SCOPUS_OUTPUT_PATH,
    'backend': 'sqlite',
    'fast_save': True,
    'extension': '.sqlite3',
    # https://requests-cache.readthedocs.io/en/latest/user_guide.html#expiration
    'expire_after': timedelta(hours=24)
})

'''
def clear_cache(msid):
    requests_cache.core.get_cache().delete_url(glencoe_url(msid))
'''

def _search(api_key, doi_prefix, page=0, per_page=25):
    "searches scopus"
    params = {
        'query': 'DOI("%s/*")' % doi_prefix,
        #'field': 'citedby-count', # not too useful unless we combine it with other fields
        #'view': 'COMPLETE' # verboten
        'start': page, # a 400 is thrown when we page out
        'count': per_page,
    }
    LOG.info('calling scopus with params: %s', params)
    headers = {
        'Accept': 'application/json',
        'X-ELS-APIKey': api_key,
    }
    # https://dev.elsevier.com/tecdoc_cited_by_in_scopus.html
    # http://api.elsevier.com/documentation/SCOPUSSearchAPI.wadl
    url = "http://api.elsevier.com/content/search/scopus"
    response = requests.get(url, params=params, headers=headers)
    # throw an exception if we get a non-2xx response
    # http://docs.python-requests.org/en/master/user/quickstart/#response-status-codes
    response.raise_for_status()

    # deserialize their json
    return response.json()

def search(api_key=settings.SCOPUS_KEY, doi_prefix=settings.DOI_PREFIX):
    """searches scopus, returning a generator that will iterate through each page
    of results until all pages have been consumed.

    results are cached and expire daily"""
    page = 0
    per_page = 25 # max per page

    data = _search(api_key, doi_prefix, page=page, per_page=per_page)

    # generate some boring pagination helpers
    total_results = int(data['search-results']['opensearch:totalResults']) # ll: 3592
    total_pages = int(math.ceil(total_results / per_page)) # ll: 144

    yield data['search-results']

    start_page = page + 1 # we've already fetched the first page, start at second page
    for page in range(start_page, total_pages):
        data = _search(api_key, doi_prefix, page=page, per_page=per_page)
        yield data['search-results']

def _extract(search_result_entry):
    "ingests a single search result from scopus"
    data = search_result_entry
    citedby_link = first(filter(lambda d: d["@ref"] == "scopus-citedby", data['link']))
    return {
        'doi': data['prism:doi'],
        'num': int(data['citedby-count']),
        'source': models.SCOPUS,
        'source_id': citedby_link['@href']
    }

def extract(search_result):
    "extracts citation counts from a page of search results from scopus"
    return map(_extract, search_result['entry'])

def all_entries(search_result_list):
    "returns a list of 'entries', citation information for articles from a list of search result pages"
    return flatten(map(extract, search_result_list))


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
    return filter(not_abstract, all_entries(list(search())))
