import requests
from dateutil.relativedelta import relativedelta
from article_metrics import models, utils, handler
from django.conf import settings
import logging

from xml.dom.minidom import parseString

LOG = logging.getLogger(__name__)

URL = "https://doi.crossref.org/servlet/getForwardLinks"

class FetchCrossrefCitationsError(RuntimeError):
    pass

def fetch(doi):
    LOG.info("fetching crossref citations for %s" % doi)
    params = {
        # include citations from posted content (including preprints)
        'include_postedcontent': 'true',
        'usr': settings.CROSSREF_USER,
        'pwd': settings.CROSSREF_PASS,
        'doi': doi,
        'startDate': utils.ymd(settings.INCEPTION),
        # this value must be relatively static to avoid cache misses every day as endDate changes
        # this gives us the first of next month. on that day, we'll get misses despite caching expiry
        'endDate': utils.ymd(utils.utcnow() + relativedelta(months=1, day=1)),
    }
    headers = {
        'Accept': 'application/json'
    }
    try:
        resp = handler.requests_get(URL, params=params, headers=headers, opts={
            401: handler.LOGIT, # when a doi gets into system (like via scopus) that crossref doesn't associate with account
            404: handler.IGNORE, # these happen often for articles with 0 citations
        })
        return resp.content if resp else None
    except requests.exceptions.RequestException:ß
        raise FetchCrossrefCitationsError(f'failled to fetch crossref citation for {doi}')

@handler.capture_parse_error
def parse(xmlbytes, doi):
    if not xmlbytes:
        # nothing to parse, carry on
        return None
    dom = parseString(xmlbytes)
    body = dom.getElementsByTagName('body')[0]
    citations = body.getElementsByTagName('forward_link')
    return {
        'doi': doi,
        'num': len(citations),
        'source': models.CROSSREF,
        'source_id': 'https://doi.org/' + doi
    }

def count_for_doi(doi, include_all_versions=False):
    try:
        results = parse(fetch(doi), doi)
        if results and include_all_versions:
            count_for_versions = 0
            for version in utils.get_article_versions(utils.doi2msid(doi)):
                v_doi = f"{doi}.{version}"
                v_results = parse(fetch(v_doi), v_doi)

                if v_results:
                    count_for_versions += v_results['num']

            results['num'] += count_for_versions

        return results
    except FetchCrossrefCitationsError as e:
        LOG.warning('%r', e)
        return None


def count_for_msid(msid):
    return count_for_doi(utils.msid2doi(msid))

def count_for_qs(qs):
    for art in qs:
        yield count_for_doi(art.doi, include_all_versions=True)

#
#
#

def citations_for_all_articles():
    return count_for_qs(models.Article.objects.all())
