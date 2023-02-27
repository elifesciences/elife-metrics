import json
from . import base
from unittest import mock
from datetime import date, datetime
from metrics import ga4
#from django.test import override_settings
import pytest
from article_metrics import utils
import os

@pytest.fixture(name="tempdir")
def _tempdir():
    path, closer = utils.tempdir()
    yield path
    closer()

def test_build_ga4_query__queries_for_frame():
    expected = {
        "dimensions": [{"name": "date"},
                       {"name": "pagePathPlusQueryString"}],
        "metrics": [{"name": "sessions"}],
        "dateRanges": [{"startDate": "2023-01-01",
                        "endDate": "2023-01-31"}],
        "dimensionFilter": {
            "filter": {
                "fieldName": "pagePathPlusQueryString",
                "stringFilter": {
                    "matchType": "BEGINS_WITH",
                    "value": "/inside-elife"}}},
        "limit": "10000"}

    start_dt = datetime(year=2023, month=1, day=1)
    end_dt = datetime(year=2023, month=1, day=31)

    frame = {'prefix': '/inside-elife'}

    actual = ga4.build_ga4_query__queries_for_frame(None, frame, start_dt, end_dt)
    assert actual == expected

def test_query_ga(tempdir):
    """not a great test, but essentially we expect `ga4.query_ga` to query ga and return
    the results from GA without modification, writing a cache file as a side effect.
    """
    frame = {'prefix': '/inside-elife'}
    start_dt = datetime(year=2023, month=1, day=1)
    end_dt = datetime(year=2023, month=1, day=31)
    query = ga4.build_ga4_query__queries_for_frame(None, frame, start_dt, end_dt)

    results_type = 'blog-article'

    expected = fixture = json.loads(open(base.fixture_path('ga4-response--blog-articles.json'), 'r').read())

    output_path = os.path.join(tempdir, 'foo.json')
    with mock.patch('article_metrics.ga_metrics.core.output_path_v2', return_value=output_path):
        with mock.patch('article_metrics.ga_metrics.ga4.query_ga', return_value=fixture):
            actual = ga4.query_ga(results_type, query, None)

    assert actual == expected
    assert os.path.exists(output_path)
    assert json.loads(open(output_path, 'r').read()) == expected

def test_process_response():
    expected = [
        {'date': date(2023, 1, 2), 'identifier': '54d63486', 'views': 157},
        {'date': date(2023, 1, 1), 'identifier': '54d63486', 'views': 75},
        {'date': date(2023, 1, 2), 'identifier': 'ebadb0f1', 'views': 20},
        {'date': date(2023, 1, 2), 'identifier': '', 'views': 10},
        {'date': date(2023, 1, 1), 'identifier': 'ebadb0f1', 'views': 9},
        {'date': date(2023, 1, 2), 'identifier': '6794cd8a', 'views': 7},
        {'date': date(2023, 1, 1), 'identifier': '6794cd8a', 'views': 5},
        {'date': date(2023, 1, 2), 'identifier': '85518309', 'views': 5},
        {'date': date(2023, 1, 2), 'identifier': 'db24dd46', 'views': 5},
        {'date': date(2023, 1, 2), 'identifier': 'ddab483b', 'views': 5}]
    ptype = 'blog-article'
    frame = {'prefix': '/inside-elife'}
    response = json.loads(open(base.fixture_path('ga4-response--blog-articles.json'), 'r').read())
    actual = ga4.process_response(ptype, frame, response)
    assert actual[:10] == expected[:10]
