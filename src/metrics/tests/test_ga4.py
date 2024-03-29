import json
from . import base
from unittest import mock
from datetime import date, datetime
from metrics import ga4
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
        "orderBys": [
                {"desc": True,
                 "dimension": {"dimensionName": "date",
                               "orderType": "NUMERIC"}}],
        "limit": "10000"}

    start_dt = datetime(year=2023, month=1, day=1)
    end_dt = datetime(year=2023, month=1, day=31)

    frame = {'id': 'foo',
             'prefix': '/inside-elife',
             'starts': start_dt,
             'ends': end_dt}

    ptype = None
    actual = ga4.build_ga4_query__queries_for_frame(ptype, frame, start_dt, end_dt)
    assert actual == expected

def test_query_ga(tempdir):
    """not a great test, but essentially we expect `ga4.query_ga` to query ga and return
    the results from GA without modification, writing a cache file as a side effect.
    """
    start_dt = datetime(year=2023, month=1, day=1)
    end_dt = datetime(year=2023, month=1, day=31)
    frame = {'id': 'foo',
             'prefix': '/inside-elife',
             'starts': start_dt,
             'ends': end_dt}

    ptype = None
    query = ga4.build_ga4_query__queries_for_frame(ptype, frame, start_dt, end_dt)

    results_type = 'blog-article'

    expected = fixture = json.load(open(base.fixture_path('ga4-response--blog-articles.json'), 'r'))

    output_path = os.path.join(tempdir, 'foo.json')
    with mock.patch('article_metrics.ga_metrics.core.output_path_v2', return_value=output_path):
        with mock.patch('article_metrics.ga_metrics.ga4.query_ga', return_value=fixture):
            actual = ga4.query_ga(results_type, query, None)

    assert actual == expected
    assert os.path.exists(output_path)
    assert json.load(open(output_path, 'r')) == expected

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
    response = json.load(open(base.fixture_path('ga4-response--blog-articles.json'), 'r'))
    actual = ga4.process_response(ptype, frame, response)
    assert actual[:10] == expected[:10]

def test_process_response__other_row():
    expected = []
    expected_error = "skipping row, bad value: path does not start with given prefix ('/inside-elife'): (other)"
    ptype = 'blog-article'
    frame = {'prefix': '/inside-elife'}
    response = json.load(open(base.fixture_path('ga4-response--other_row.json'), 'r'))
    with mock.patch('metrics.ga4.LOG') as log:
        actual = ga4.process_response(ptype, frame, response)
        assert actual == expected
        assert log.error.call_count == 1
        assert log.error.call_args.args[0] == expected_error

def test_prefixed_path_id():
    "a prefix is stripped from a path and the first of any remaining path segments is returned"
    cases = [
        ("/pants/foobar", "foobar"),
        ("/pants/foo/bar", "foo"),
        ("https://sub.example.org/pants/foo/bar", "foo"),
        ("/pants/foo?bar=baz", "foo"),
        ("/pants/foo?bar=baz&bup=", "foo"),
        ("/pants/foo#bar", "foo"),
        ("/pants/foo#bar?baz=bup", "foo"),
    ]
    for given, expected in cases:
        assert ga4.prefixed_path_id('/pants', given) == expected
