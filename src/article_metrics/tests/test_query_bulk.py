from unittest import mock
from . import base
from datetime import timedelta
from article_metrics.ga_metrics import core
from collections import Counter

def test_daily_query_results_correct_pre_switch():
    "the results from a query (pre-switch) are calculated correctly"
    from_date = to_date = core.SITE_SWITCH - timedelta(days=1)
    fixture_path = base.fixture_path('views-2016-02-08.json')

    with mock.patch('article_metrics.ga_metrics.core.output_path', return_value=fixture_path):
        counts = core.article_views(base.TABLE_ID, from_date, to_date, cached=True)

    expected = {
        '10.7554/eLife.10778': Counter({'full': 119, 'abstract': 10, 'digest': 1}),
        '10.7554/eLife.10509': Counter({'full': 11, 'abstract': 2, 'digest': 0}),
        '10.7554/eLife.09560': Counter({'full': 182, 'abstract': 17, 'digest': 0}),
    }
    for key, expected_val in expected.items():
        assert counts[key] == expected_val
