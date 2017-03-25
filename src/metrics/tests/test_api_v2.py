import json
from metrics import models
from django.test import Client
from . import base
from django.core.urlresolvers import reverse
from metrics.utils import ymd, ym, utcnow

class ApiV2(base.BaseCase):
    def setUp(self):
        self.c = Client()
        self.metric_list = ['citations', 'downloads', 'page-views']

    def tearDown(self):
        pass

    def test_order_param_on_citations(self):
        "the '?order=' parameter affecting result ordering"
        cases = {
            # msid, citations, downloads, views
            # crossref, scopus, pubmed
            '1234': ([
                2, # crossref
                3, # scopus
                1, # pubmed
            ], 0, 0),
        }
        base.insert_metrics(cases)

        expected_response = [
            {
                'service': models.PUBMED,
                'uri': 'asdf',
                'citations': 1
            },
            {
                'service': models.CROSSREF,
                'uri': 'asdf',
                'citations': 2
            },
            {
                'service': models.SCOPUS,
                'uri': 'asdf',
                'citations': 3
            },

        ]
        url = reverse('v2:alm', kwargs={'id': 1234, 'metric': 'citations'})
        resp = self.c.get(url, {'order': 'asc'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(base.resp_json(resp), expected_response)

    def test_order_param_on_citations_rev(self):
        "the '?order=' parameter affecting result ordering"
        cases = {
            # msid, citations, downloads, views
            # crossref, scopus, pubmed
            '1234': ([
                2, # crossref
                3, # scopus
                1, # pubmed
            ], 0, 0),
        }
        base.insert_metrics(cases)

        expected_response = [
            {
                'service': models.SCOPUS,
                'uri': 'asdf',
                'citations': 3
            },
            {
                'service': models.CROSSREF,
                'uri': 'asdf',
                'citations': 2
            },
            {
                'service': models.PUBMED,
                'uri': 'asdf',
                'citations': 1
            },
        ]
        url = reverse('v2:alm', kwargs={'id': 1234, 'metric': 'citations'})
        resp = self.c.get(url, {'order': 'desc'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(base.resp_json(resp), expected_response)

    def test_non_int_page_param(self):
        "a '?page=foo' type param results in a 400 error"
        for metric in self.metric_list:
            url = reverse('v2:alm', kwargs={'id': '9560', 'metric': metric})
            resp = self.c.get(url, {'page': 'pants'})
            self.assertEqual(resp.status_code, 400)

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
            },
            {
                'service': models.SCOPUS,
                'uri': '',
                'citations': 0
            },
            {
                'service': models.PUBMED,
                'uri': '',
                'citations': 0
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
        "a request for an article that exists but has no citations returns a list of citation providers with a count of zero"
        base.insert_metrics({'1234': (0, 0, 0)})
        url = reverse('v2:alm', kwargs={'id': 1234, 'metric': 'citations'})
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200)
        expected_response = [
            {
                'service': models.CROSSREF,
                'uri': '',
                'citations': 0
            },
            {
                'service': models.PUBMED,
                'uri': '',
                'citations': 0
            },
            {
                'service': models.SCOPUS,
                'uri': '',
                'citations': 0
            }
        ]
        actual_response = resp.data
        self.assertCountEqual(expected_response, actual_response)

    def test_daily_views(self):
        cases = {
            1234: (0, 0, 1)
        }
        base.insert_metrics(cases)
        expected_response = {
            'totalPeriods': 1,
            'totalValue': 1,
            'periods': [
                {
                    'period': ymd(utcnow()),
                    'value': 1
                }
            ]
        }
        url = reverse('v2:alm', kwargs={'id': 1234, 'metric': 'page-views'})
        resp = self.c.get(url, {'by': models.DAY})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(expected_response, resp.data)

    def test_daily_downloads(self):
        cases = {
            1234: (0, 1, 0)
        }
        base.insert_metrics(cases)
        expected_response = {
            'totalPeriods': 1,
            'totalValue': 1,
            'periods': [
                {
                    'period': ymd(),
                    'value': 1
                }
            ]
        }
        url = reverse('v2:alm', kwargs={'id': 1234, 'metric': 'downloads'})
        resp = self.c.get(url, {'by': models.DAY})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(expected_response, resp.data)

    def test_monthly_views(self):
        cases = {
            1234: (0, 0, 1, models.MONTH)
        }
        base.insert_metrics(cases)
        expected_response = {
            'totalPeriods': 1,
            'totalValue': 1,
            'periods': [
                {
                    'period': ym(),
                    'value': 1
                }
            ]
        }
        url = reverse('v2:alm', kwargs={'id': 1234, 'metric': 'page-views'})
        resp = self.c.get(url, {'by': models.MONTH})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(expected_response, resp.data)

    def test_monthly_downloads(self):
        cases = {
            1234: (0, 1, 0, models.MONTH)
        }
        base.insert_metrics(cases)
        expected_response = {
            'totalPeriods': 1,
            'totalValue': 1,
            'periods': [
                {
                    'period': ym(),
                    'value': 1
                }
            ]
        }
        url = reverse('v2:alm', kwargs={'id': 1234, 'metric': 'downloads'})
        resp = self.c.get(url, {'by': models.MONTH})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(expected_response, resp.data)
