from os.path import join
import requests  # , math
import logging
import requests_cache
from django.conf import settings
from datetime import timedelta
from metrics import models # good idea reaching back?
from metrics.utils import first, flatten

LOG = logging.getLogger(__name__)

requests_cache.install_cache(**{
    'cache_name': join(settings.SCOPUS_OUTPUT_PATH, 'db'),
    'backend': 'sqlite',
    'fast_save': True,
    'extension': '.sqlite3',
    # https://requests-cache.readthedocs.io/en/latest/user_guide.html#expiration
    'expire_after': timedelta(hours=24 * 7)
})


def clear_cache():
    requests_cache.clear()


def _search(api_key, doi_prefix, page=0, per_page=25):
    "searches scopus"
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

    yield data['search-results']

    # I think this is 'total pages'
    # you can certainly query far far beyond 'totalResults / per_page'
    total_pages = int(data['search-results']['opensearch:totalResults'])

    # I think we're capped at 10k/day ? can't find their docs on this
    # eLife tends to hit 0 citations at about the 2.5k mark
    max_pages = 5000
    try:
        for page in range(page + 1, total_pages):
            LOG.info("page %r", page)

            try:
                if page == max_pages:
                    raise GeneratorExit("hit max pages (%s)" % max_pages)

                data = _search(api_key, doi_prefix, page=page, per_page=per_page)
                yield data['search-results']

                # exit early if we start hitting 0 results
                fentry = data['search-results']['entry'][0]['citedby-count']
                if int(fentry) == 0:
                    raise GeneratorExit("no more articles with citations")
                LOG.info("fentry: %r", fentry)

            except requests.HTTPError as err:
                raise GeneratorExit(str(err))

    except GeneratorExit:
        return

def _extract(search_result_entry):
    "ingests a single search result from scopus"
    data = search_result_entry
    citedby_link = first(filter(lambda d: d["@ref"] == "scopus-citedby", data['link']))
    try:
        return {
            'doi': data['prism:doi'],
            'num': int(data['citedby-count']),
            'source': models.SCOPUS,
            'source_id': citedby_link['@href']
        }
    except KeyError:
        LOG.error("key error for: %s", search_result_entry)
        return {'bad': search_result_entry}

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
    # return filter(not_abstract, all_entries(list(search())))
    return all_entries(list(search()))
