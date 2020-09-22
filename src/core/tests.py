from django.test import TestCase, Client

class DownstreamCachine(TestCase):
    def setUp(self):
        self.c = Client()
        self.url = '/' # we could hit more urls but it's applied application-wide

    def tearDown(self):
        pass

    def test_cache_headers_in_response(self):
        expected_headers = [
            'vary',
            'cache-control'
        ]
        resp = self.c.get(self.url)
        for header in expected_headers:
            self.assertTrue(resp.has_header(header), "header %r not found in response" % header)

    def test_cache_headers_not_in_response(self):
        cases = [
            'expires',
            'last-modified',
            'prama'
        ]
        resp = self.c.get(self.url)
        for header in cases:
            self.assertFalse(resp.has_header(header), "header %r present in response" % header)
