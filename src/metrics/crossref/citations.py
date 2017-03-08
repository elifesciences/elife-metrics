from os.path import join
import requests
import requests_cache
from metrics import utils
from metrics import models
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

def _fetch(doi):
    LOG.info("fetching crossref citations for %s" % doi)
    params = {
        'usr': settings.CROSSREF_USER,
        'pwd': settings.CROSSREF_PASS,
        'doi': doi,
        'startDate': utils.ymd(settings.INCEPTION),
        'endDate': utils.ymd(utils.utcnow() + timedelta(days=1)),
    }
    headers = {
        'Accept': 'application/json'
    }
    url = "https://doi.crossref.org/servlet/getForwardLinks"
    try:
        resp = requests.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.content
    except requests.HTTPError as err:
        status_code = err.response.status_code
        if status_code != 404:
            LOG.error("error response attempting to fetch citation count from crossref for article %s: %s", doi, err)

def parse(doi, xmlbytes):
    if not xmlbytes:
        # nothing to parse, carry on
        return None
    dom = parseString(xmlbytes)
    body = dom.getElementsByTagName('body')[0]
    citations = body.getElementsByTagName('forward_link')
    #doi = citations[0].getAttribute('doi')
    return {
        'doi': doi,
        'num': len(citations),
        'source': models.CROSSREF,
        'source_id': 'https://doi.org/' + doi
    }

def count_for_doi(doi):
    return parse(doi, _fetch(doi))

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
