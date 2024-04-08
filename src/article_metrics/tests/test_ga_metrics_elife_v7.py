from unittest import mock
from article_metrics.ga_metrics import elife_v7

def mk_view(path, value):
    return {"dimensionValues": [{"value": path}], "metricValues": [{"value": str(value)}]}

def mkrow(path, value):
    return {"dimensionValues": [{"value": "Download"}, {"value": path}], "metricValues": [{"value": str(value)}]}

def test_path_count():
    expected = ('09560', 'full', 1)
    fixture = mk_view("/articles/09560", "1")
    actual = elife_v7.path_count(fixture)
    assert actual == expected

    expected = ('09560', 'full', 1)
    fixture = mk_view("/reviewed-preprints/09560", "1")
    actual = elife_v7.path_count(fixture)
    assert actual == expected

def test_path_counts__bad_cases():
    cases = [
        (None, 0, 0),
        ({}, 0, 0),
        ([], 0, 0),
        ([{}], 0, 1),
        ([{'dimensionValues': []}], 0, 1),
        ([{'dimensionValues': [], 'metricValues': []}], 0, 1),
        ([{'dimensionValues': [{'foo': 'bar'}], 'metricValues': []}], 0, 1),
        ([{'dimensionValues': [{'foo': 'bar'}, {'baz': 'bup'}], 'metricValues': [{'foo': 'bar'}]}], 0, 1),
    ]
    for rows, expected, expected_warnings in cases:
        with mock.patch('article_metrics.ga_metrics.elife_v7.LOG.warning') as m:
            actual = elife_v7.path_counts(rows)
            assert len(actual) == expected, "case: %s" % rows
            assert m.call_count == expected_warnings

def test_path_count__bad_article():
    expected = None
    expected_msg = "ignoring article views row: failed to find a valid path: /articles/1234567"
    fixture = mk_view("/articles/1234567", "1") # 7 digit msid, max is 6
    with mock.patch('article_metrics.ga_metrics.elife_v7.LOG') as log:
        actual = elife_v7.path_count(fixture)
        assert actual == expected
        assert log.warning.call_args[0][0] == expected_msg

def test_path_count__bad_rpp():
    expected = None
    expected_msg = "ignoring article views row: failed to find a valid path: /reviewed-preprints/1234567"
    fixture = mk_view("/reviewed-preprints/1234567", "1") # 7 digit msid, max is 6
    with mock.patch('article_metrics.ga_metrics.elife_v7.LOG') as log:
        actual = elife_v7.path_count(fixture)
        assert actual == expected
        assert log.warning.call_args[0][0] == expected_msg

def test_event_count__article():
    expected = (80092, 717)
    fixture = mkrow("/articles/80092", "717")
    actual = elife_v7.event_count(fixture)
    assert actual == expected

def test_event_count__rpp():
    expected = (80092, 717)
    fixture = mkrow("/reviewed-preprints/80092", "717")
    actual = elife_v7.event_count(fixture)
    assert actual == expected
    
def test_event_count__bad_article():
    expected = None
    expected_msg = "ignoring article downloads row: failed to find a valid path: /articles/12345/foo"
    fixture = mkrow("/articles/12345/foo", "717")
    with mock.patch('article_metrics.ga_metrics.elife_v7.LOG') as log:
        actual = elife_v7.event_count(fixture)
        assert actual == expected
        assert log.warning.call_args[0][0] == expected_msg

def test_event_count__bad_rpp():
    expected = None
    expected_msg = "ignoring article downloads row: failed to find a valid path: /reviewed-preprints/12345/foo"
    fixture = mkrow("/reviewed-preprints/12345/foo", "717")
    with mock.patch('article_metrics.ga_metrics.elife_v7.LOG') as log:
        actual = elife_v7.event_count(fixture)
        assert actual == expected
        assert log.warning.call_args[0][0] == expected_msg
        
def test_event_count__other():
    expected = None
    expected_msg = "ignoring article downloads row: found 'other' row with value '717'. GA has aggregated rows because query returned too much data."
    fixture = mkrow("(other)", "717")
    with mock.patch('article_metrics.ga_metrics.elife_v7.LOG') as log:
        actual = elife_v7.event_count(fixture)
        assert actual == expected
        assert log.warning.call_args[0][0] == expected_msg

def test_event_counts__bad_cases():
    cases = [
        (None, 0, 0),
        ({}, 0, 0),
        ([], 0, 0),
        ([{}], 0, 1),
        ([{'dimensionValues': []}], 0, 1),
        ([{'dimensionValues': [], 'metricValues': []}], 0, 1),
        ([{'dimensionValues': [{'foo': 'bar'}], 'metricValues': []}], 0, 1),
        ([{'dimensionValues': [{'foo': 'bar'}, {'baz': 'bup'}], 'metricValues': [{'foo': 'bar'}]}], 0, 1),
    ]
    for rows, expected, expected_warnings in cases:
        with mock.patch('article_metrics.ga_metrics.elife_v7.LOG.warning') as m:
            actual = elife_v7.event_counts(rows)
            assert len(actual) == expected, "case: %s" % rows
            assert m.call_count == expected_warnings

def test_event_counts():
    expected = {
        '10.7554/eLife.90561': 1,
        '10.7554/eLife.90562': 2,
        '10.7554/eLife.90563': 7,
    }
    fixture = [
        mkrow("/articles/90561", 1),
        mkrow("/articles/90562", 2),
        mkrow("/articles/90563", 3),
        mkrow("/reviewed-preprints/90563", 4),
    ]
    actual = elife_v7.event_counts(fixture)
    assert actual == expected

def test_event_counts__multiple_counts():
    expected = {
        '10.7554/eLife.90560': 10,
    }
    fixture = [
        mkrow("/articles/90560", 1),
        mkrow("/articles/90560", 2),
        mkrow("/articles/90560", 3),
        mkrow("/reviewed-preprints/90560", 4),
    ]
    actual = elife_v7.event_counts(fixture)
    assert actual == expected
