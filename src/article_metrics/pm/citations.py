from article_metrics import models, utils, handler
from article_metrics.utils import ensure, lmap, subdict, first, lfilter
import requests
from django.conf import settings
import logging

LOG = logging.getLogger(__name__)

PM_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
PMID_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"

MAX_PER_PAGE = 200 # we can actually go as high as ~800

def norm_pmcid(pmcid):
    "returns the integer form of a pmc id, stripping any leading 'pmc' prefix."
    if not pmcid:
        return None
    if str(pmcid).lower().startswith('pmc'):
        return pmcid[3:]
    return str(pmcid)

def _fetch_pmids(doi):
    # article doesn't have a pmcid for whatever reason
    # go fetch one using doi
    # https://www.ncbi.nlm.nih.gov/pmc/tools/id-converter-api/
    LOG.info("fetching pmcid for doi %s" % doi)
    params = {
        'ids': doi,
        'tool': 'elife-metrics',
        'email': settings.CONTACT_EMAIL,
        'format': 'json',
    }
    resp = requests.get(PMID_URL, params=params)
    resp.raise_for_status()

    data = resp.json()
    # ll:
    # {
    # "status": "ok",
    # "responseDate": "2017-01-31 13:35:10",
    # "request": "ids=10.7554%2FeLife.09560;format=json",
    # "records": [
    #   {
    #    "pmcid": "PMC4559886",
    #    "pmid": "26354291",
    #    "doi": "10.7554/eLife.09560",
    #    "versions": [
    #      {
    #       "pmcid": "PMC4559886.1",
    #       "current": "true"
    #      }
    #    ]
    #   }
    # ]
    # }
    ensure(data['status'] == 'ok', "response is not ok! %s" % data)
    return subdict(data['records'][0], ['pmid', 'pmcid'])

def resolve_pmcid(artobj):
    pmcid = artobj.pmcid
    if pmcid:
        LOG.debug("no pmcid fetch necessary")
        return pmcid
    data = _fetch_pmids(artobj.doi)
    data['doi'] = artobj.doi # don't use doi from response, prefer the doi we already have
    artobj = first(utils.create_or_update(models.Article, data, ['doi'], create=False, update=True))
    return artobj.pmcid

#
#
#

def fetch(pmcid_list):
    pmcid_list_len = len(list(pmcid_list))
    ensure(pmcid_list_len <= MAX_PER_PAGE,
           "no more than %s results can be processed per-request. requested: %s" % (MAX_PER_PAGE, pmcid_list_len))
    headers = {
        'accept': 'application/json'
    }
    params = {
        'dbfrom': 'pubmed',
        'linkname': 'pmc_pmc_citedby',
        'id': [norm_pmcid(pmcid) for pmcid in pmcid_list if pmcid],
        'tool': 'elife-metrics',
        'email': settings.CONTACT_EMAIL,
        'retmode': 'json'
    }
    return handler.requests_get(PM_URL, params=params, headers=headers)

@handler.capture_parse_error
def parse_result(result):
    if 'linksetdbs' in result:
        cited_by = result['linksetdbs'][0]['links']
    else:
        cited_by = []
    pmcid = 'PMC' + str(result['ids'][0]) # there can be more than one
    return {
        'pmcid': pmcid,
        'source': models.PUBMED,
        'source_id': "https://www.ncbi.nlm.nih.gov/pmc/articles/%s/" % pmcid,
        'num': len(cited_by),
        # 'links': cited_by # PMC ids of articles linking to this one
    }

#
#
#

def fetch_parse(pmcid_list):
    "pages through all results for a list of PMC ids (can be just one) and parses the results."
    results = []

    for page, sub_pmcid_list in enumerate(utils.paginate(pmcid_list, MAX_PER_PAGE)):
        LOG.debug("page %s, %s per-page", page + 1, MAX_PER_PAGE)

        resp = fetch(sub_pmcid_list)
        result = resp.json()["linksets"]
        # result is a list of maps. add all maps returned to a single list ...
        results.extend(result)
    # ... to be parsed all at once.
    return lmap(parse_result, results)

def fetch_parse_v2(pmcid_list):
    """pages through all results for a list of PMC ids (can be just one) and parses the results.
    version 2 processes results lazily.
    the given `pmcid_list` doesn't *have* to be lazy but it's probably best."""
    for page, sub_pmcid_list in enumerate(utils.paginate_v2(pmcid_list, MAX_PER_PAGE)):
        LOG.debug("page %s, %s per-page", page + 1, MAX_PER_PAGE)
        resp = fetch(sub_pmcid_list)
        for result in resp.json()["linksets"]:
            yield parse_result(result)

def process_results(results):
    "post process the parsed results"

    def good_row(row):
        # need to figure out where these are sneaking in
        return row['pmcid'] != 'PMC0'

    data = lfilter(good_row, results)
    return data

def process_results_v2(results):
    """post process the parsed results.
    version 2 processes the results lazily."""

    def good_row(row):
        # need to figure out where these are sneaking in
        return row['pmcid'] != 'PMC0'

    return filter(good_row, results)

#
# results for individual articles
# request overhead is low
#

def count_for_obj(art):
    return process_results(fetch_parse([resolve_pmcid(art)]))

def count_for_doi(doi):
    return count_for_obj(models.Article.objects.get(doi=doi))

def count_for_msid(msid):
    return count_for_obj(models.Article.objects.get(doi=utils.msid2doi(msid)))

#
# results for many articles
# request overhead is HIGH if pmcids haven't been loaded
#

def count_for_qs(qs):
    """the queryset `qs` fetches objects in chunks of 2000 by default when using iterator().
    `resolve_pmcid` will consume each of those objects one by one,
    possibly doing a network fetch and a db upsert if IDs are not present,
    and yielding a list of maps behind it.k
    `fetch_parse_v2` will consume this list in batches of `MAX_PER_PAGE`,
    processing each search result in the page before yielding them individually to logic.import_pmc_citations,
    that will upsert (or not) each result into the db individually."""
    return process_results_v2(fetch_parse_v2(map(resolve_pmcid, qs)))

def citations_for_all_articles():
    return count_for_qs(models.Article.objects.all().iterator())
