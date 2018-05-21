import json
from article_metrics import models, utils
from django.test import Client
from . import base
from django.core.urlresolvers import reverse

class ApiV2(base.BaseCase):
    def setUp(self):
        self.c = Client()
        self.metric_list = ['citations', 'downloads', 'page-views']

    def tearDown(self):
        pass

    def test_ping(self):
        resp = self.c.get(reverse('v2:ping'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, 'text/plain; charset=UTF-8')
        self.assertEqual(resp['Cache-Control'], 'must-revalidate, no-cache, no-store, private')
        self.assertEqual(resp.content.decode('utf-8'), 'pong')

    def test_order_param_on_citations(self):
        "the '?order=' parameter affecting result ordering"
        cases = {
            # msid, citations, downloads, views
            '1234': ([
                2, # crossref
                3, # scopus
                1, # pubmed
            ], 0, 0),
        }
        base.insert_metrics(cases)

        expected_response = [
            {
                'service': models.PUBMED_LABEL,
                'uri': 'asdf',
                'citations': 1
            },
            {
                'service': models.CROSSREF_LABEL,
                'uri': 'asdf',
                'citations': 2
            },
            {
                'service': models.SCOPUS_LABEL,
                'uri': 'asdf',
                'citations': 3
            },
        ]
        url = reverse('v2:alm', kwargs={'msid': 1234, 'metric': 'citations'})
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
                'service': models.SCOPUS_LABEL,
                'uri': 'asdf',
                'citations': 3
            },
            {
                'service': models.CROSSREF_LABEL,
                'uri': 'asdf',
                'citations': 2
            },
            {
                'service': models.PUBMED_LABEL,
                'uri': 'asdf',
                'citations': 1
            },
        ]
        url = reverse('v2:alm', kwargs={'msid': 1234, 'metric': 'citations'})
        resp = self.c.get(url, {'order': 'desc'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(base.resp_json(resp), expected_response)

    def test_non_int_page_param(self):
        "a '?page=foo' type param results in a 400 error"
        for metric in self.metric_list:
            url = reverse('v2:alm', kwargs={'msid': '9560', 'metric': metric})
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
                url = reverse('v2:alm', kwargs={'msid': msid, 'metric': metric})
                resp = self.c.get(url)
                # all requests are successful
                self.assertEqual(resp.status_code, 200)
                # all requests return json
                # json.loads(resp.bytes.decode('utf-8')) # python3
                json.loads(resp.content.decode('utf-8'))

    # WARN! non-deterministic results!
    def test_citations(self):
        cases = {
            '5678': (23, 0, 0)
        }
        base.insert_metrics(cases)

        expected_response = [
            {
                'service': models.CROSSREF_LABEL,
                'uri': 'asdf',
                'citations': 23
            },
            {
                'service': models.PUBMED_LABEL,
                'uri': '',
                'citations': 0
            },
            {
                'service': models.SCOPUS_LABEL,
                'uri': '',
                'citations': 0
            }
        ]
        url = reverse('v2:alm', kwargs={'msid': 5678, 'metric': 'citations'})
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200)
        actual_response = resp.data
        self.assertEqual(expected_response, actual_response)

    def test_citations_missing_article(self):
        "a request for an article that doesn't exist raises a 404"
        url = reverse('v2:alm', kwargs={'msid': 1234, 'metric': 'citations'})
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_citations_missing_citations(self):
        "a request for an article that exists but has no citations returns a list of citation providers with a count of zero"
        base.insert_metrics({'1234': (0, 0, 0)})
        url = reverse('v2:alm', kwargs={'msid': 1234, 'metric': 'citations'})
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200)
        expected_response = [
            {
                'service': models.CROSSREF_LABEL,
                'uri': '',
                'citations': 0
            },
            {
                'service': models.PUBMED_LABEL,
                'uri': '',
                'citations': 0
            },
            {
                'service': models.SCOPUS_LABEL,
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
                    'period': '2001-01-01',
                    'value': 1
                }
            ]
        }
        url = reverse('v2:alm', kwargs={'msid': 1234, 'metric': 'page-views'})
        resp = self.c.get(url, {'by': models.DAY})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(expected_response, resp.data)

    def test_daily_views2(self):
        "all three of full, abstract and digest daily views are counted"
        cases = {
            1234: (0, 0, (1, 2, 3))
        }
        base.insert_metrics(cases)
        expected_response = {
            'totalPeriods': 1,
            'totalValue': 6,
            'periods': [
                {
                    'period': '2001-01-01',
                    'value': 6
                }
            ]
        }
        url = reverse('v2:alm', kwargs={'msid': 1234, 'metric': 'page-views'})
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
                    'period': '2001-01-01',
                    'value': 1
                }
            ]
        }
        url = reverse('v2:alm', kwargs={'msid': 1234, 'metric': 'downloads'})
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
                    'period': '2001-01',
                    'value': 1
                }
            ]
        }
        url = reverse('v2:alm', kwargs={'msid': 1234, 'metric': 'page-views'})
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
                    'period': '2001-01',
                    'value': 1
                }
            ]
        }
        url = reverse('v2:alm', kwargs={'msid': 1234, 'metric': 'downloads'})
        resp = self.c.get(url, {'by': models.MONTH})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(expected_response, resp.data)

class Three(base.BaseCase):
    def setUp(self):
        self.c = Client()

    def tearDown(self):
        pass

    def test_results_empty_summary(self):
        url = reverse('v2:summary')
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200)

        expected_response = {
            'total': 0,
            'items': []
        }
        self.assertEqual(resp.json(), expected_response)

    def test_results_single_summary(self):
        cases = {
            # msid, citations, downloads, views
            '1234': ([
                2, # crossref
                3, # scopus
                1, # pubmed
            ], 10, 11),
        }
        base.insert_metrics(cases)

        expected_response = {
            'total': 1,
            'items': [{
                'id': 1234,
                'views': 11,
                'downloads': 10,
                models.CROSSREF: 2,
                models.PUBMED: 1,
                models.SCOPUS: 3
            }]
        }

        url = reverse('v2:summary')
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), expected_response)

    def test_results_multiple_summary(self):
        cases = {
            '1111': ([1, 1, 1], 1, 1),
            '2222': ([2, 2, 2], 2, 2),
            '3333': ([3, 3, 3], 3, 3),
        }
        base.insert_metrics(cases)

        expected_response = {
            'total': 3,
            'items': [
                # default ordering per API is DESC
                # default ordering key for articles is DOI
                {'id': 3333, 'views': 3, 'downloads': 3, models.CROSSREF: 3, models.PUBMED: 3, models.SCOPUS: 3},
                {'id': 2222, 'views': 2, 'downloads': 2, models.CROSSREF: 2, models.PUBMED: 2, models.SCOPUS: 2},
                {'id': 1111, 'views': 1, 'downloads': 1, models.CROSSREF: 1, models.PUBMED: 1, models.SCOPUS: 1},
            ]
        }

        url = reverse('v2:summary')
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), expected_response)

    def test_paginate_results(self):
        cases = {
            '1111': ([1, 1, 1], 1, 1),
            '2222': ([2, 2, 2], 2, 2),
            '3333': ([3, 3, 3], 3, 3),
        }
        base.insert_metrics(cases)

        page_cases = [
            {'total': 3, 'items': [
                {'id': 1111, 'views': 1, 'downloads': 1, models.CROSSREF: 1, models.PUBMED: 1, models.SCOPUS: 1},
            ]},
            {'total': 3, 'items': [
                {'id': 2222, 'views': 2, 'downloads': 2, models.CROSSREF: 2, models.PUBMED: 2, models.SCOPUS: 2},
            ]},
            {'total': 3, 'items': [
                {'id': 3333, 'views': 3, 'downloads': 3, models.CROSSREF: 3, models.PUBMED: 3, models.SCOPUS: 3}
            ]},
        ]
        for page, expected_response in enumerate(page_cases):
            page += 1 # enumerate is zero-based
            url = reverse('v2:summary')
            resp = self.c.get(url, {'page': page, 'per-page': 1, 'order': 'asc'})
            self.assertEqual(resp.json(), expected_response)

    def test_one_bad_apple(self):
        "articles with bad dois don't prevent an entire summary from being returned"
        cases = {
            '1111': ([1, 1, 1], 1, 1),
            '2222': ([2, 2, 2], 2, 2),
        }
        base.insert_metrics(cases)

        # skitch doi
        # this is the particular bad doi I'm dealing with right now
        bad_doi = '10.7554/eLife.00000'
        models.Article.objects.filter(doi=utils.msid2doi('1111')).update(doi=bad_doi)

        # expect just one result
        resp = self.c.get(reverse('v2:summary'))
        expected_response = {
            'total': 1,
            'items': [
                {'id': 2222, 'views': 2, 'downloads': 2, models.CROSSREF: 2, models.PUBMED: 2, models.SCOPUS: 2},
            ]
        }
        self.assertEqual(resp.json(), expected_response)

class Four(base.BaseCase):
    def setUp(self):
        self.c = Client()

    def tearDown(self):
        pass

    def test_results_single_article_summary(self):
        "summaries can be provided on a per-article basis. results are the same as regular summary, just reduced to one item"
        cases = {
            # msid, citations, downloads, views
            '1234': ([
                2, # crossref
                3, # scopus
                1, # pubmed
            ], 10, 11),
        }
        base.insert_metrics(cases)

        expected_response = {
            'total': 1,
            'items': [{
                'id': 1234,
                'views': 11,
                'downloads': 10,
                models.CROSSREF: 2,
                models.PUBMED: 1,
                models.SCOPUS: 3
            }]
        }

        url = reverse('v2:article-summary', kwargs={'msid': 1234})
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), expected_response)

    def test_no_single_article_summary(self):
        url = reverse('v2:article-summary', kwargs={'msid': 1234})
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_one_bad_apple(self):
        "bad article objects are removed from results"
        cases = {
            '1111': ([1, 1, 1], 1, 1),
            '2222': ([2, 2, 2], 2, 2),
        }
        base.insert_metrics(cases)

        # skitch doi
        # this is the particular bad doi I'm dealing with right now
        bad_doi = '10.7554/eLife.e30552' # preceeding 'e'
        models.Article.objects.filter(doi=utils.msid2doi('1111')).update(doi=bad_doi)

        url = reverse('v2:summary')
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200)

        expected_response = {
            'total': 2, # BUG: incorrect, should be 1, but won't-fix. this is a data and ingestion problem
            'items': [{
                'id': 2222,
                'views': 2,
                'downloads': 2,
                models.CROSSREF: 2,
                models.PUBMED: 2,
                models.SCOPUS: 2
            }]
        }
        self.assertEqual(resp.json(), expected_response)
