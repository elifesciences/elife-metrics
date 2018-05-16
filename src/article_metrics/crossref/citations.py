from dateutil.relativedelta import relativedelta
from metrics import models, utils, handler
from django.conf import settings
import logging

from xml.dom.minidom import parseString

LOG = logging.getLogger(__name__)

URL = "https://doi.crossref.org/servlet/getForwardLinks"

def fetch(doi):
    LOG.info("fetching crossref citations for %s" % doi)
    params = {
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
    resp = handler.requests_get(URL, params=params, headers=headers, opts={
        401: handler.LOGIT, # when a doi gets into system (like via scopus) that crossref doesn't associate with account
        404: handler.IGNORE, # these happen often for articles with 0 citations
    })
    return resp.content if resp else None

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

def count_for_doi(doi):
    return parse(fetch(doi), doi)

def count_for_msid(msid):
    return count_for_doi(utils.msid2doi(msid))

def count_for_qs(qs):
    for art in qs:
        yield count_for_doi(art.doi)

#
#
#

def citations_for_all_articles():
    return count_for_qs(models.Article.objects.all())
