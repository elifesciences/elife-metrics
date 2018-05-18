from os.path import join
from . import base
import json
from datetime import datetime, timedelta
from article_metrics import utils
from article_metrics.ga_metrics import core
from collections import Counter
from unittest.mock import patch

class TestQueryResults(base.SimpleBaseCase):
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

    def test_daily_query_results_correct_post_switch(self):
        "the results from a query (post-switch) are calculated correctly"
        from_date = to_date = core.SITE_SWITCH + timedelta(days=1) # day after
        counts = core.article_views(self.table_id, from_date, to_date, cached=True)
        expected = {
            '10.7554/eLife.10518': Counter({'abstract': 0, 'digest': 1, 'full': 4}),
            '10.7554/eLife.10921': Counter({'abstract': 0, 'digest': 2, 'full': 153}),
            '10.7554/eLife.12620': Counter({'abstract': 29, 'digest': 4, 'full': 2053}),
        }
        for key, expected_val in expected.items():
            self.assertEqual(expected_val, counts[key])

class Two(base.SimpleBaseCase):
    def setUp(self):
        self.fixture_path = join(self.fixture_dir, '2017-10-01_2017-10-31.json.partial')
        self.fixture = json.load(open(self.fixture_path, 'r'))

        # this fixture has a number of bad paths:
        self.bad_eggs = [
            ['/articles/004071', '1'],
            ['/articles/121771', '1'],
            ['/articles/2212815887', '1'],
            ['/articles/292222222222222222222222222222222222222222222222222222222222222', '1'],
            ['/articles/2922222222222222222222222222222222222222222222222222222222222229999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999', '2'],
            ['/articles/305610', '1'],
        ]

    def test_elife_v4_excludes_bad_paths(self):
        from_dt, to_dt = datetime(2017, 10, 1), datetime(2017, 10, 31)
        with patch('article_metrics.ga_metrics.core.query_ga_write_results', return_value=(self.fixture, self.fixture_path)):
            with patch('article_metrics.ga_metrics.core.output_path', return_value=self.fixture_path):
                results = core.article_views('0xdeadbeef', from_dt, to_dt, cached=False, only_cached=False)
                # total raw results = 4501
                # after filtering bad eggs and aggregation: 4491
                expected = 4491
                self.assertEqual(expected, len(results))

        final_doi_list = list(results.values())
        for path in dict(self.bad_eggs).values():
            doi = utils.pad_msid(path.rsplit('/', 1)[-1])
            self.assertTrue(doi not in final_doi_list)
