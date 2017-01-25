import json
from metrics import models
from django.test import Client
import base
from django.core.urlresolvers import reverse

class ApiV2(base.BaseCase):
    def setUp(self):
        self.c = Client()

    def tearDown(self):
        pass

    def test_api(self):
        cases = {
            # msid, citations, downloads, views
            '1234': (1, 2, 3),
            '5677': (4, 6, 7)
        }
        base.insert_metrics(cases)

        metric_list = ['citations', 'downloads', 'page-views']
        for msid, expected in cases.items():
            # go through each metric type and request the value
            for metric_idx, expected_val in enumerate(expected):
                metric = metric_list[metric_idx]
                url = reverse('v2:alm', kwargs={'id': msid, 'metric': metric})
                resp = self.c.get(url)
                # all requests are successful
                self.assertEqual(resp.status_code, 200)
                # all requests return json
                # json.loads(resp.bytes.decode('utf-8')) # python3
                json.loads(resp.content.decode('utf-8'))

    def test_citations(self):
        cases = {
            '5678': (23, 0, 0)
        }
        base.insert_metrics(cases)

        expected_response = [
            {
                'service': models.CROSSREF,
                'uri': 'asdf',
                'citations': 23
            }
        ]
        url = reverse('v2:alm', kwargs={'id': 5678, 'metric': 'citations'})
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200)
        actual_response = resp.data
        self.assertEqual(expected_response, actual_response)

    def test_citations_missing_article(self):
        "a request for an article that doesn't exist raises a 404"
        url = reverse('v2:alm', kwargs={'id': 1234, 'metric': 'citations'})
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_citations_missing_citations(self):
        "a request for an article that exists but has no citations returns an empty response"
        base.insert_metrics({'1234': (0, 0, 0)})
        url = reverse('v2:alm', kwargs={'id': 1234, 'metric': 'citations'})
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200)
        expected_response = []
        actual_response = resp.data
        self.assertEqual(expected_response, actual_response)

    def test_views(self):
        case = {
            '1234': (0, 0, 1)
        }
        print case
