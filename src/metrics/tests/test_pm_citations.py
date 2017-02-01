import base
from metrics.pm import citations
from metrics import models

class PM(base.BaseCase):
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
            'pmcid': 'NOT-A-PMCID',
        })
        art.save()
        given = citations.resolve_pmcid(art)
        expected = 'NOT-A-PMCID'
        self.assertEqual(expected, given)
        models.Article.objects.get(pmcid=expected)

    def test_citation_fetch(self):
        given = citations._fetch([self.pmcid])
        for toplevel in ['header', 'linksets']:
            self.assertTrue(toplevel in given)
        expected = 1 # one result
        self.assertTrue(expected, len(given['linksets']))

        print 'given', given

        result = given['linksets'][0]
        self.assertTrue('linksetdbs' in result)
        self.assertTrue(len(result['linksetdbs'][0]['links']) >= 12)
