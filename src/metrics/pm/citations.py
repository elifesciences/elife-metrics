from metrics import models, utils
import requests

def fetch(pmcid):
    if pmcid.lower().startswith('pmc'):
        pmcid = pmcid[3:]
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&linkname=pmc_pmc_citedby&id=3557905&tool=my_tool&email=my_email@example.com"

    headers = {
        'accept': 'application/json'
    }
    params = {
        'dbfrom': 'pubmed',
        'linkname': 'pmc_pmc_citedby',
        'id': pmcid,
        'tool': 'elife-metrics',
        'email': 'it-admin@elifesciences.org',
        'retmode': 'json'
    }
    resp = requests.get(url, params=params, headers=headers)
    # raise error if error
    return resp

def parse_resp(resp):
    # there are two 'linksets' with identical content ..
    return len(resp.json()['linksets'][0]['linksetdbs'][0]['links'])

def count_for_obj(art):
    if not art.pmcid:
        # TODO:
        raise ValueError("art has no pmcid")
    return parse_resp(fetch(art.pmcid))

def count_for_doi(doi):
    return count_for_obj(models.Article.objects.get(doi=doi))

def count_for_msid(msid):
    return count_for_obj(models.Article.objects.get(doi=utils.msid2doi(msid)))
