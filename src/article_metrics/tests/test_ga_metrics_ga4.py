import pytest
from datetime import datetime
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

def test_query_ga_hard_fail_invalid_date():
    now = datetime(year=2015, month=6, day=1)
    cases = [
        ('2015-05-31', '2015-05-31'), # yesterday, invalid, die
        ('2015-06-01', '2015-06-01'), # today, invalid, die
        ('2015-06-02', '2015-06-02'), # tomorrow, invalid, die
    ]
    query = {'dateRanges': [{'startDate': None, 'endDate': None}]}
    with mock.patch('article_metrics.ga_metrics.ga4.datetime_now', return_value=now):
        with pytest.raises(AssertionError):
            for start_date, end_date in cases:
                query['dateRanges'][0]['startDate'] = start_date
                query['dateRanges'][0]['endDate'] = end_date
                ga4.query_ga(query)
