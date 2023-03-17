from unittest import mock
from article_metrics.ga_metrics import elife_v7

def test_path_count():
    expected = ('09560', 'full', 1)
    fixture = {
        "dimensionValues": [
            {
                "value": "/articles/09560"
            }
        ],
        "metricValues": [
            {
                "value": "1"
            }
        ]
    }
    actual = elife_v7.path_count(fixture)
    assert actual == expected

def test_path_count__bad_article():
    expected = None
    expected_msg = "ignoring article views row, failed to find a valid path: /articles/1234567"
    fixture = {
        "dimensionValues": [
            {
                "value": "/articles/1234567"
            }
        ],
        "metricValues": [
            {
                "value": "1"
            }
        ]
    }
    with mock.patch('article_metrics.ga_metrics.elife_v7.LOG') as log:
        actual = elife_v7.path_count(fixture)
        assert actual == expected
        assert log.debug.call_args[0][0] == expected_msg

def test_event_count():
    expected = (80092, 717)
    fixture = {
        "dimensionValues": [
            {
                "value": "Download"
            },
            {
                "value": "/articles/80092"
            }
        ],
        "metricValues": [
            {
                "value": "717"
            }
        ]
    }
    actual = elife_v7.event_count(fixture)
    assert actual == expected

def test_event_count__bad_article():
    expected = None
    expected_msg = "ignoring article downloads row, failed to find a valid path: /articles/12345/foo"
    fixture = {
        "dimensionValues": [
            {
                "value": "Download"
            },
            {
                "value": "/articles/12345/foo"
            }
        ],
        "metricValues": [
            {
                "value": "717"
            }
        ]
    }
    with mock.patch('article_metrics.ga_metrics.elife_v7.LOG') as log:
        actual = elife_v7.event_count(fixture)
        assert actual == expected
        assert log.debug.call_args[0][0] == expected_msg

def test_event_count__other():
    expected = None
    expected_msg = "found 'other' row with value '717'. GA has aggregated rows because query returned too much data."
    fixture = {
        "dimensionValues": [
            {
                "value": "Download"
            },
            {
                "value": "(other)"
            }
        ],
        "metricValues": [
            {
                "value": "717"
            }
        ]
    }
    with mock.patch('article_metrics.ga_metrics.elife_v7.LOG') as log:
        actual = elife_v7.event_count(fixture)
        assert actual == expected
        assert log.warning.call_args[0][0] == expected_msg

def mkrow(path, value):
    return {"dimensionValues": [{"value": "Download"}, {"value": path}], "metricValues": [{"value": str(value)}]}

def test_event_counts():
    expected = {'10.7554/eLife.90561': 1, '10.7554/eLife.90562': 2, '10.7554/eLife.90563': 3}
    fixture = [
        mkrow("/articles/90561", 1),
        mkrow("/articles/90562", 2),
        mkrow("/articles/90563", 3),
    ]
    actual = elife_v7.event_counts(fixture)
    assert actual == expected

def test_event_counts__multiple_counts():
    expected = {'10.7554/eLife.90560': 6}
    fixture = [
        mkrow("/articles/90560", 1),
        mkrow("/articles/90560", 2),
        mkrow("/articles/90560", 3),
    ]
    actual = elife_v7.event_counts(fixture)
    assert actual == expected
