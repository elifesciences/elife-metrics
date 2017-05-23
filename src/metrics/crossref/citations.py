from dateutil.relativedelta import relativedelta
from os.path import join
import requests_cache
from metrics import models, utils, handler
from django.conf import settings
from datetime import timedelta
import logging

from xml.dom.minidom import parseString

LOG = logging.getLogger(__name__)

requests_cache.install_cache(**{
    'cache_name': join(settings.CROSSREF_OUTPUT_PATH, 'db'),
    'backend': 'sqlite',
    'fast_save': True,
    'extension': '.sqlite3',
    # https://requests-cache.readthedocs.io/en/latest/user_guide.html#expiration
    'expire_after': timedelta(hours=24 * settings.CROSSREF_CACHE_EXPIRY)
})

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
    url = "https://doi.crossref.org/servlet/getForwardLinks"
    resp = handler.requests_get(url, params=params, headers=headers, opts={
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
