import json
from unittest import mock
from article_metrics.ga_metrics import ga4
from .base import fixture_path

def test_query_ga():
    expected = {
        # result of last response ...
        'dimensionHeaders': [{'name': 'pagePathPlusQueryString'}],
        'metricHeaders': [{'name': 'sessions', 'type': 'TYPE_INTEGER'}],
        'metadata': {'currencyCode': 'USD', 'timeZone': 'America/Los_Angeles'},
        'kind': 'analyticsData#runReport',
        # ... with some additional fields
        '-total-pages': 1,
        'rows': []
    }
    query = {}
    fixture = json.load(open(fixture_path('ga4--empty-response.json'), 'r'))
    with mock.patch('article_metrics.ga_metrics.ga4._query_ga', return_value=fixture):
        actual = ga4.query_ga(query)
    assert expected == actual
