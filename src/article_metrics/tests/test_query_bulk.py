from .base import BaseCase
from datetime import timedelta
from article_metrics.ga_metrics import core
from collections import Counter

class TestQueryResults(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_daily_query_results_correct_pre_switch(self):
        "the results from a query (pre-switch) are calculated correctly"
        from_date = to_date = core.SITE_SWITCH - timedelta(days=1)
        counts = core.article_views(self.table_id, from_date, to_date)
        expected = {
            '10.7554/eLife.10778': Counter({'full': 119, 'abstract': 10, 'digest': 1}),
            '10.7554/eLife.10509': Counter({'full': 11, 'abstract': 2, 'digest': 0}),
            '10.7554/eLife.09560': Counter({'full': 182, 'abstract': 17, 'digest': 0}),
        }
        for key, expected_val in expected.items():
            self.assertEqual(expected_val, counts[key])
