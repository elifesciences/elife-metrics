import base
from metrics.scopus import citations
from django.conf import settings

class Scopus(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_scopus_request(self):
        search_gen = citations.search(settings.SCOPUS_KEY, settings.DOI_PREFIX)
        search_results = next(search_gen)
        self.assertTrue('opensearch:totalResults' in search_results)
        self.assertEqual(search_results['opensearch:startIndex'], '0')

        search_results2 = next(search_gen)
        self.assertTrue('opensearch:totalResults' in search_results)
        self.assertEqual(search_results2['opensearch:startIndex'], '1')
