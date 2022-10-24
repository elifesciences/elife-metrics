from os.path import join
import json
import responses
from . import base
from article_metrics.pm import citations
from article_metrics import models

def test_norm_pmcid():
    cases = [
        (None, None),
        ('', None),
        (1, '1'),
        (1234567, '1234567'),
        ('1234567', '1234567'),
        ('PMC1', '1'),
        ('PMC1234567', '1234567')
    ]
    for given, expected in cases:
        assert citations.norm_pmcid(given) == expected


class One(base.BaseCase):
    def setUp(self):
        self.doi = '10.7554/eLife.09560'
        self.pmid = '26354291'
        self.pmcid = 'PMC4559886'

    @responses.activate
    def test_fetch_pmids(self):
        "test that a pmid and pmcid can be fetched"
        fixture = join(self.fixture_dir, 'pm-fetch-pmids-response.json')
        expected_body_content = json.load(open(fixture, 'r'))
        responses.add(responses.GET, citations.PMID_URL, **{
            'json': expected_body_content,
            'status': 200,
            'content_type': 'application/json'})

        expected = {
            # 'doi': '10.7554/eLife.09560', # removed from response, prefer the doi we already have
            'pmid': '26354291',
            'pmcid': 'PMC4559886'
        }
        self.assertEqual(expected, citations._fetch_pmids('10.7554/eLife.09560'))

    @responses.activate
    def test_resolve_pmcid(self):
        "test that a pmid and pmcid can be fetched if an article is missing theirs"
        art = models.Article(**{
            'doi': '10.7554/eLife.09560',
            'pmid': None,
            'pmcid': None
        })
        art.save()

        fixture = join(self.fixture_dir, 'pm-fetch-pmids-response.json')
        expected_body_content = json.load(open(fixture, 'r'))
        responses.add(responses.GET, citations.PMID_URL, **{
            'json': expected_body_content,
            'status': 200,
            'content_type': 'application/json'})

        given = citations.resolve_pmcid(art)
        expected = 'PMC4559886'
        self.assertEqual(expected, given)
        models.Article.objects.get(pmcid=expected)

    # @responses.activate # unnecessary
    def test_resolve_pmcid_preexisting(self):
        "test that no lookup for a pmcid is done if Article already has such an id"
        art = models.Article(**{
            'doi': '10.7554/eLife.09560',
            'pmid': None,
            'pmcid': 'NOTAPMCID',
        })
        art.save()
        given = citations.resolve_pmcid(art)
        expected = 'NOTAPMCID'
        self.assertEqual(expected, given)
        models.Article.objects.get(pmcid=expected)

    @responses.activate
    def test_citation_fetch(self):
        fixture = join(self.fixture_dir, 'pm-citation-request-response-09560.json')
        expected_body_content = json.load(open(fixture, 'r'))
        responses.add(responses.GET, citations.PM_URL, **{
            'json': expected_body_content,
            'content_type': 'application/json'})

        result = citations.fetch([self.pmcid]).json()['linksets'][0]
        expected = 17
        self.assertEqual(len(result['linksetdbs'][0]['links']), expected)

    @responses.activate
    def test_citations_fetch_all(self):
        art = models.Article(**{
            'doi': self.doi,
            'pmid': self.pmid,
            'pmcid': self.pmcid
        })
        art.save()

        fixture = join(self.fixture_dir, 'pm-citation-request-response-09560.json')
        expected_body_content = json.load(open(fixture, 'r'))
        responses.add(responses.GET, citations.PM_URL, **{
            'json': expected_body_content,
            'status': 200,
            'content_type': 'application/json'})

        expected_citations = len(expected_body_content['linksets'][0]['linksetdbs'][0]['links'])
        expected = [{
            'source': 'pubmed',
            'pmcid': self.pmcid,
            'num': expected_citations,
            'source_id': 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4559886/'}]

        results = list(citations.citations_for_all_articles())
        assert results == expected

    @responses.activate
    def test_count_response(self):
        art = models.Article(**{
            'doi': self.doi,
            'pmid': self.pmid,
            'pmcid': self.pmcid
        })
        art.save()

        msid = 9560

        fixture = join(self.fixture_dir, 'pm-citation-request-response-09560.json')
        expected_body_content = json.load(open(fixture, 'r'))

        responses.add(responses.GET, citations.PM_URL, **{
            'json': expected_body_content,
            'status': 200,
            'content_type': 'application/json'})

        expected = [{
            'pmcid': 'PMC4559886',
            'source': 'pubmed',
            'source_id': 'https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4559886/',
            'num': 17}]

        self.assertEqual(citations.count_for_msid(msid), expected)
        self.assertEqual(citations.count_for_doi(self.doi), expected)
