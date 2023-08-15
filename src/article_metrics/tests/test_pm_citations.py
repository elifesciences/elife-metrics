import requests
import pytest
import responses
from . import base
from article_metrics.pm import citations
from article_metrics import models

def test_norm_pmcid():
    cases = [
        (None, None),
        ('', None),
        (0, '0'),
        (1, '1'),
        (1234567, '1234567'),
        ('1234567', '1234567'),
        ('PMC1', '1'),
        ('PMC1234567', '1234567')
    ]
    for given, expected in cases:
        assert expected == citations.norm_pmcid(given)

@responses.activate
def test_fetch_pmids():
    "test that a pmid and pmcid can be fetched"
    fixture = base.fixture_json('pm-fetch-pmids-response.json')
    responses.add(responses.GET, citations.PMID_URL, **{
        'json': fixture,
        'status': 200,
        'content_type': 'application/json'})
    expected = {
        'pmid': '26354291',
        'pmcid': 'PMC4559886'
    }
    assert expected == citations._fetch_pmids('10.7554/eLife.09560')

@responses.activate
@pytest.mark.django_db
def test_resolve_pmcid():
    "test that a pmid and pmcid can be fetched if an article is missing theirs"
    art = models.Article(**{
        'doi': '10.7554/eLife.09560',
        'pmid': None,
        'pmcid': None
    })
    art.save()

    fixture = base.fixture_json('pm-fetch-pmids-response.json')
    responses.add(responses.GET, citations.PMID_URL, **{
        'json': fixture,
        'status': 200,
        'content_type': 'application/json'})

    given = citations.resolve_pmcid(art)
    expected = 'PMC4559886'
    assert expected == given
    models.Article.objects.get(pmcid=expected)

@pytest.mark.django_db
def test_resolve_pmcid_preexisting():
    "test that no lookup for a pmcid is done if Article already has such an id"
    art = models.Article(**{
        'doi': '10.7554/eLife.09560',
        'pmid': None,
        'pmcid': 'NOTAPMCID',
    })
    art.save()
    given = citations.resolve_pmcid(art)
    expected = 'NOTAPMCID'
    assert expected == given
    models.Article.objects.get(pmcid=expected)

@responses.activate
def test_citation_fetch():
    fixture = base.fixture_json('pm-citation-request-response-09560.json')
    responses.add(responses.GET, citations.PM_URL, **{
        'json': fixture,
        'content_type': 'application/json'})
    pmcid = 'PMC4559886'
    result = citations.fetch([pmcid]).json()['linksets'][0]
    expected = 17
    assert expected == len(result['linksetdbs'][0]['links'])

@responses.activate
def test_citation_fetch__failed():
    responses.add(responses.GET, citations.PM_URL, body=requests.exceptions.RetryError())
    pmcid = 'PMC4559886'
    assert citations.fetch([pmcid]) is None

@responses.activate
def test_fetch_parse__failed():
    responses.add(responses.GET, citations.PM_URL, body=requests.exceptions.RetryError())
    pmcid = 'PMC4559886'
    assert list(citations.fetch_parse([pmcid])) == []

@responses.activate
def test_fetch_parse_v2__failed():
    responses.add(responses.GET, citations.PM_URL, body=requests.exceptions.RetryError())
    pmcid = 'PMC4559886'
    assert list(citations.fetch_parse_v2([pmcid])) == []

@responses.activate
@pytest.mark.django_db
def test_citations_fetch_all():
    doi = '10.7554/eLife.09560'
    pmid = '26354291'
    pmcid = 'PMC4559886'
    art = models.Article(**{
        'doi': doi,
        'pmid': pmid,
        'pmcid': pmcid
    })
    art.save()

    fixture = base.fixture_json('pm-citation-request-response-09560.json')
    responses.add(responses.GET, citations.PM_URL, **{
        'json': fixture,
        'status': 200,
        'content_type': 'application/json'})

    expected_citations = len(fixture['linksets'][0]['linksetdbs'][0]['links'])
    expected = [{
        'source': 'pubmed',
        'pmcid': pmcid,
        'num': expected_citations,
        'source_id': 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4559886/'}]

    results = list(citations.citations_for_all_articles())
    assert expected == results

@responses.activate
@pytest.mark.django_db
def test_count_response():
    msid = 9560
    doi = '10.7554/eLife.09560'
    pmid = '26354291'
    pmcid = 'PMC4559886'
    art = models.Article(**{
        'doi': doi,
        'pmid': pmid,
        'pmcid': pmcid
    })
    art.save()

    fixture = base.fixture_json('pm-citation-request-response-09560.json')
    responses.add(responses.GET, citations.PM_URL, **{
        'json': fixture,
        'status': 200,
        'content_type': 'application/json'})

    expected = [{
        'pmcid': 'PMC4559886',
        'source': 'pubmed',
        'source_id': 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4559886/',
        'num': 17}]

    assert expected == citations.count_for_msid(msid)
    assert expected == citations.count_for_doi(doi)
