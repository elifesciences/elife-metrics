import pytest
import json
from article_metrics import models, utils
from django.test import Client
from . import base
from django.urls import reverse

def test_ping():
    resp = Client().get(reverse('v2:ping'))
    assert resp.status_code == 200
    assert resp.content_type == 'text/plain; charset=UTF-8'
    assert resp['Cache-Control'] == 'must-revalidate, no-cache, no-store, private'
    assert resp.content.decode('utf-8') == 'pong'

@pytest.mark.django_db
def test_order_param_on_citations():
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
    resp = Client().get(url, {'order': 'asc'})
    assert resp.status_code == 200
    assert expected_response == resp.json()

@pytest.mark.django_db
def test_order_param_on_citations_rev():
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
    resp = Client().get(url, {'order': 'desc'})
    assert resp.status_code == 200
    assert resp.json() == expected_response

def test_non_int_page_param():
    "a '?page=foo' type param results in a 400 error"
    client = Client()
    for metric in ['citations', 'downloads', 'page-views']:
        url = reverse('v2:alm', kwargs={'msid': '9560', 'metric': metric})
        resp = client.get(url, {'page': 'pants'})
        assert resp.status_code == 400

@pytest.mark.django_db
def test_api():
    client = Client()
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
            resp = client.get(url)
            # all requests are successful
            assert resp.status_code == 200
            # all requests return json
            json.loads(resp.content.decode('utf-8'))

# WARN! non-deterministic results!
@pytest.mark.django_db
def test_citations():
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
    resp = Client().get(url)
    assert resp.status_code == 200
    actual_response = resp.data
    assert expected_response == actual_response

@pytest.mark.django_db
def test_citations_missing_article():
    "a request for an article that doesn't exist raises a 404"
    url = reverse('v2:alm', kwargs={'msid': 1234, 'metric': 'citations'})
    resp = Client().get(url)
    assert resp.status_code == 404

@pytest.mark.django_db
def test_citations_missing_citations():
    "a request for an article that exists but has no citations returns a list of citation providers with a count of zero"
    base.insert_metrics({'1234': (0, 0, 0)})
    url = reverse('v2:alm', kwargs={'msid': 1234, 'metric': 'citations'})
    resp = Client().get(url)
    assert resp.status_code == 200
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
    assert len(expected_response) == len(actual_response)

@pytest.mark.django_db
def test_daily_views():
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
    resp = Client().get(url, {'by': models.DAY})
    assert resp.status_code == 200
    assert expected_response == resp.data

@pytest.mark.django_db
def test_daily_views2():
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
    resp = Client().get(url, {'by': models.DAY})
    assert resp.status_code == 200
    assert expected_response == resp.data

@pytest.mark.django_db
def test_daily_downloads():
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
    resp = Client().get(url, {'by': models.DAY})
    assert resp.status_code == 200
    assert expected_response == resp.data

@pytest.mark.django_db
def test_monthly_views():
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
    resp = Client().get(url, {'by': models.MONTH})
    assert resp.status_code == 200
    assert expected_response == resp.data

@pytest.mark.django_db
def test_monthly_downloads():
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
    resp = Client().get(url, {'by': models.MONTH})
    assert resp.status_code == 200
    assert expected_response == resp.data

@pytest.mark.django_db
def test_results_empty_summary():
    url = reverse('v2:summary')
    resp = Client().get(url)
    assert resp.status_code == 200

    expected_response = {
        'total': 0,
        'items': []
    }
    assert resp.json() == expected_response

@pytest.mark.django_db
def test_results_single_summary():
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
    resp = Client().get(url)
    assert resp.status_code == 200
    assert resp.json() == expected_response

@pytest.mark.django_db
def test_results_multiple_summary():
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
    resp = Client().get(url)
    assert resp.status_code == 200
    assert resp.json() == expected_response

@pytest.mark.django_db
def test_paginate_results():
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
    client = Client()
    for page, expected_response in enumerate(page_cases):
        page += 1 # enumerate is zero-based
        url = reverse('v2:summary')
        resp = client.get(url, {'page': page, 'per-page': 1, 'order': 'asc'})
        assert resp.json() == expected_response

@pytest.mark.django_db
def test_one_bad_apple_1():
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
    resp = Client().get(reverse('v2:summary'))
    expected_response = {
        'total': 1,
        'items': [
            {'id': 2222, 'views': 2, 'downloads': 2, models.CROSSREF: 2, models.PUBMED: 2, models.SCOPUS: 2},
        ]
    }
    assert resp.json() == expected_response

@pytest.mark.django_db
def test_results_single_article_summary():
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
    resp = Client().get(url)
    assert resp.status_code == 200
    assert resp.json() == expected_response

@pytest.mark.django_db
def test_no_single_article_summary():
    url = reverse('v2:article-summary', kwargs={'msid': 1234})
    resp = Client().get(url)
    assert resp.status_code == 404

@pytest.mark.django_db
def test_one_bad_apple_2():
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
    resp = Client().get(url)
    assert resp.status_code == 200

    expected_response = {
        'total': 1,
        'items': [{
            'id': 2222,
            'views': 2,
            'downloads': 2,
            models.CROSSREF: 2,
            models.PUBMED: 2,
            models.SCOPUS: 2
        }]
    }
    assert resp.json() == expected_response
