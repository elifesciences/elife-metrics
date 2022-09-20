from os.path import join
from . import base
import json
from datetime import datetime, timedelta
from article_metrics import utils
from article_metrics.ga_metrics import core, elife_v1
from collections import Counter
from unittest.mock import patch

class V3V4Transition(base.SimpleBaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_daily_query_results_correct_pre_switch(self):
        "the results from a query (pre-switch) are calculated correctly"
        from_date = to_date = core.SITE_SWITCH - timedelta(days=1)

        fixture = base.fixture_path('views-2016-02-08.json')
        with patch('article_metrics.ga_metrics.core.output_path', return_value=fixture):
            counts = core.article_views(self.table_id, from_date, to_date, cached=True)

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

        fixture = base.fixture_path('views-2016-02-10.json')
        with patch('article_metrics.ga_metrics.core.output_path', return_value=fixture):
            counts = core.article_views(self.table_id, from_date, to_date, cached=True)

        expected = {
            '10.7554/eLife.10518': Counter({'abstract': 0, 'digest': 1, 'full': 4}),
            '10.7554/eLife.10921': Counter({'abstract': 0, 'digest': 2, 'full': 153}),
            '10.7554/eLife.12620': Counter({'abstract': 29, 'digest': 4, 'full': 2053}),
        }
        for key, expected_val in expected.items():
            self.assertEqual(expected_val, counts[key])

class V4(base.SimpleBaseCase):
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


class V5(base.SimpleBaseCase):
    "v5 era is the same as v4, except /executable is added to list of article paths to include."

    def test_v5_daily(self):
        "the daily `/article/123` and `/article/123/executable` sums add up"
        fixture_path = join(self.fixture_dir, 'v5--views--2020-02-22.json')
        fixture = json.load(open(fixture_path, 'r'))

        from_dt = to_dt = datetime(2020, 2, 22) # daily
        with patch('article_metrics.ga_metrics.core.query_ga_write_results', return_value=(fixture, fixture_path)):
            with patch('article_metrics.ga_metrics.core.output_path', return_value=fixture_path):
                ga_table_id = '0xdeadbeef'
                results = core.article_views(ga_table_id, from_dt, to_dt, cached=False, only_cached=False)
                expected_total_results = 4491 # total results after counting (not rows in fixture)
                expected_total = Counter(full=379200, abstract=0, digest=0) # total of all results

                # mix of `/article` and `/article/executable`
                expected_sample = {
                    48: Counter(full=48, abstract=0, digest=0),
                    68: Counter(full=2, abstract=0, digest=0),
                    78: Counter(full=30, abstract=0, digest=0),

                    90: Counter(full=38, abstract=0, digest=0)
                }

                self.assertEqual(expected_total_results, len(results))
                self.assertEqual(expected_total, elife_v1.count_counter_list(results.values()))
                for msid, expected_count in expected_sample.items():
                    self.assertEqual(expected_count, results[utils.msid2doi(msid)])

    def test_v5_monthly(self):
        "the monthly `/article/123` and `/article/123/executable` sums add up"
        fixture_path = join(self.fixture_dir, 'v5--views--2020-03-01_2020-03-31.json')
        fixture = json.load(open(fixture_path, 'r'))

        from_dt, to_dt = datetime(2020, 3, 1), datetime(2020, 3, 31) # monthly
        with patch('article_metrics.ga_metrics.core.query_ga_write_results', return_value=(fixture, fixture_path)):
            with patch('article_metrics.ga_metrics.core.output_path', return_value=fixture_path):
                ga_table_id = '0xdeadbeef'
                results = core.article_views(ga_table_id, from_dt, to_dt, cached=False, only_cached=False)

                expected_total_results = 4491 # total results after counting (not rows in fixture)
                expected_total = Counter(full=379200, abstract=0, digest=0) # total of all results

                # mix of `/article` and `/article/executable`
                expected_sample = {
                    48: Counter(full=48, abstract=0, digest=0),
                    68: Counter(full=2, abstract=0, digest=0),
                    78: Counter(full=30, abstract=0, digest=0),

                    90: Counter(full=38, abstract=0, digest=0)
                }

                self.assertEqual(expected_total_results, len(results))
                self.assertEqual(expected_total, elife_v1.count_counter_list(results.values()))
                for msid, expected_count in expected_sample.items():
                    self.assertEqual(expected_count, results[utils.msid2doi(msid)])

class V6(base.SimpleBaseCase):
    "v6 era is the same as v5, except paths containing certain url parameters are included."

    def test_v6_daily(self):
        fixture_path = join(self.fixture_dir, 'v6--views--2021-11-30.json')
        fixture = json.load(open(fixture_path, 'r'))

        from_dt = to_dt = datetime(2021, 12, 1) # daily
        with patch('article_metrics.ga_metrics.core.query_ga_write_results', return_value=(fixture, fixture_path)):
            with patch('article_metrics.ga_metrics.core.output_path', return_value=fixture_path):
                ga_table_id = '0xdeadbeef'
                results = core.article_views(ga_table_id, from_dt, to_dt, cached=False, only_cached=False)
                expected_num_results = 7265
                expected_total = Counter(full=31275, abstract=0, digest=0)

                # representative sample of `/article` and `/article/executable`, /article?foo=...
                expected_sample = [
                    (61268, Counter(full=7, abstract=0, digest=0)),
                    (60066, Counter(full=4, abstract=0, digest=0)),
                    (61523, Counter(full=5, abstract=0, digest=0)),
                    (64909, Counter(full=17, abstract=0, digest=0)),
                    (60095, Counter(full=1, abstract=0, digest=0)),
                    (30274, Counter(full=8, abstract=0, digest=0)),
                    (48, Counter(full=1, abstract=0, digest=0)),
                    (78, Counter(full=1, abstract=0, digest=0)),
                ]

                self.assertEqual(expected_num_results, len(results))
                self.assertEqual(expected_total, elife_v1.count_counter_list(results.values()))
                for msid, expected_count in expected_sample:
                    self.assertEqual(expected_count, results[utils.msid2doi(msid)])

    def test_v6_monthly(self):
        fixture_path = join(self.fixture_dir, 'v6--views--2021-11-01_2021-11-30.json')
        fixture = json.load(open(fixture_path, 'r'))

        # it's a 2021-11 fixture but we'll use 2021-12 dates so that the v6 module is picked.
        from_dt, to_dt = datetime(2021, 12, 1), datetime(2021, 12, 31) # monthly
        with patch('article_metrics.ga_metrics.core.query_ga_write_results', return_value=(fixture, fixture_path)):
            with patch('article_metrics.ga_metrics.core.output_path', return_value=fixture_path):
                ga_table_id = '0xdeadbeef'
                results = core.article_views(ga_table_id, from_dt, to_dt, cached=False, only_cached=False)
                expected_num_results = 11738
                expected_total = Counter(full=712582, abstract=0, digest=0)

                # representative sample of `/article` and `/article/executable`, /article?foo=...
                expected_sample = [
                    (61268, Counter(full=209, abstract=0, digest=0)),
                    (60066, Counter(full=814, abstract=0, digest=0)),
                    (61523, Counter(full=127, abstract=0, digest=0)),
                    (64909, Counter(full=422, abstract=0, digest=0)),
                    (60095, Counter(full=64, abstract=0, digest=0)),
                    (30274, Counter(full=82, abstract=0, digest=0)),
                    (48, Counter(full=2, abstract=0, digest=0)),
                    (78, Counter(full=3, abstract=0, digest=0)),
                ]

                self.assertEqual(expected_num_results, len(results))
                self.assertEqual(expected_total, elife_v1.count_counter_list(results.values()))
                for msid, expected_count in expected_sample:
                    self.assertEqual(expected_count, results[utils.msid2doi(msid)])
