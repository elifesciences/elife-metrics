from os.path import join
import json
import responses
from . import base
from article_metrics.pm import citations
from article_metrics import models

class One(base.BaseCase):
    def setUp(self):
        self.doi = '10.7554/eLife.09560'
        self.pmid = '26354291'
        self.pmcid = 'PMC4559886'

    def test_norm_pmcid(self):
        cases = [
            (1, '1'),
            (1234567, '1234567'),
            ('1234567', '1234567'),
            ('PMC1', '1'),
            ('PMC1234567', '1234567')
        ]
        for given, expected in cases:
            self.assertEqual(expected, citations.norm_pmcid(given))

    def test_fetch_pmids(self):
        "test that a pmid and pmcid can be fetched"
        expected = {
            'doi': '10.7554/eLife.09560',
            'pmid': '26354291',
            'pmcid': 'PMC4559886'
        }
        self.assertEqual(expected, citations._fetch_pmids('10.7554/eLife.09560'))

    def test_resolve_pmcid(self):
        "test that a pmid and pmcid can be fetched if an article is missing theirs"
        art = models.Article(**{
            'doi': '10.7554/eLife.09560',
            'pmid': None,
            'pmcid': None
        })
        art.save()
        given = citations.resolve_pmcid(art)
        expected = 'PMC4559886'
        self.assertEqual(expected, given)
        models.Article.objects.get(pmcid=expected)

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

    def test_citation_fetch(self):
        given = citations.fetch([self.pmcid]).json()
        for toplevel in ['header', 'linksets']:
            self.assertTrue(toplevel in given)
        expected = 1 # one result
        self.assertTrue(expected, len(given['linksets']))

        result = given['linksets'][0]
        self.assertTrue('linksetdbs' in result)
        self.assertTrue(len(result['linksetdbs'][0]['links']) >= 12)

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

        citations.citations_for_all_articles()

    @responses.activate
    def test_count_for_blah(self):
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

        citations.count_for_msid(msid)
        citations.count_for_doi(self.doi)
