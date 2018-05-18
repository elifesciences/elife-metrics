from article_metrics import models, utils, handler
from article_metrics.utils import ensure, lmap, subdict, first, lfilter
import requests
from django.conf import settings
import logging

LOG = logging.getLogger(__name__)

def norm_pmcid(pmcid):
    "returns the integer form of a pmc id, stripping any leading 'pmc' prefix."
    if str(pmcid).lower().startswith('pmc'):
        return pmcid[3:]
    return str(pmcid)

MAX_PER_PAGE = 200 # we can actually go as high as ~800


def _fetch_pmids(doi):
    # article doesn't have a pmcid for whatever reason
    # go fetch one using doi
    # https://www.ncbi.nlm.nih.gov/pmc/tools/id-converter-api/
    LOG.info("fetching pmcid for doi %s" % doi)
    url = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    params = {
        'ids': doi,
        'tool': 'elife-metrics',
        'email': settings.CONTACT_EMAIL,
        'format': 'json',
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()

    data = resp.json()
    # ll:
    #{
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
    #}
    ensure(data['status'] == 'ok', "response is not ok! %s" % data)
    return subdict(data['records'][0], ['doi', 'pmid', 'pmcid'])

def resolve_pmcid(artobj):
    pmcid = artobj.pmcid
    if pmcid:
        LOG.debug("no pmcid fetch necessary")
        return pmcid
    data = _fetch_pmids(artobj.doi)
    return first(utils.create_or_update(models.Article, data, ['doi'], create=False, update=True)).pmcid

#
#
#

PM_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"

def fetch(pmcid_list):
    ensure(len(pmcid_list) <= MAX_PER_PAGE,
           "no more than %s can be processed per-request. requested: %s" % (MAX_PER_PAGE, len(pmcid_list)))
    headers = {
        'accept': 'application/json'
    }
    params = {
        'dbfrom': 'pubmed',
        'linkname': 'pmc_pmc_citedby',
        'id': lmap(norm_pmcid, pmcid_list),
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
        #'links': cited_by # PMC ids of articles linking to this one
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

def process_results(results):
    "post process the parsed results"

    def good_row(row):
        # need to figure out where these are sneaking in
        return row['pmcid'] != 'PMC0'

    data = lfilter(good_row, results)
    return data

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
    return process_results(fetch_parse(lmap(resolve_pmcid, qs)))

def citations_for_all_articles():
    return count_for_qs(models.Article.objects.all())
