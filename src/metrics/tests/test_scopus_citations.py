import base
from metrics.scopus import citations
from django.conf import settings

class Scopus(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_scopus_request(self):
        search_results = citations.search(settings.SCOPUS_KEY, settings.DOI_PREFIX)
        #print search_results
        self.assertTrue('opensearch:totalResults' in search_results['data'])
