import time
import responses
from mock import patch
import base
from metrics.scopus import citations
from django.conf import settings

class One(base.BaseCase):
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

    @responses.activate
    def test_many_scopus_requests(self):
        "scopus isn't hit more than N times a second"

        # don't actually hit scopus
        responses.add(responses.GET, citations.URL, **{
            'body': '',
            'status': 200,
            'content_type': 'text/plain'})

        with patch('metrics.handler.requests_get') as mock:
            start = time.time()
            # attempt to do more per-second than allowed
            for i in range(0, citations.MAX_PER_SECOND + 1):
                citations.fetch_page(**{
                    'api_key': 'foo',
                    'doi_prefix': settings.DOI_PREFIX,
                    'page': i
                })
            end = time.time()
            elapsed = end - start # seconds

            # doing N + 1 requests takes longer than 1 second
            self.assertTrue(elapsed > 1)
            self.assertEqual(len(mock.mock_calls), citations.MAX_PER_SECOND + 1)
