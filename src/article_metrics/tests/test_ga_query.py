import pytest
from . import base
import json
from datetime import datetime, timedelta
from article_metrics import utils
from article_metrics.ga_metrics import utils as ga_utils, core, elife_v1
from collections import Counter
from unittest.mock import patch

@pytest.mark.django_db
def test_daily_query_results_correct_pre_switch():
    "the results from a query (pre-switch) are calculated correctly"
    from_date = to_date = core.SITE_SWITCH - timedelta(days=1)
    fixture_path = base.fixture_path('views-2016-02-08.json')

    table_id = ''
    with patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture_path):
        counts = core.article_views(table_id, from_date, to_date, cached=True)

    expected = {
        '10.7554/eLife.10778': Counter({'full': 119, 'abstract': 10, 'digest': 1}),
        '10.7554/eLife.10509': Counter({'full': 11, 'abstract': 2, 'digest': 0}),
        '10.7554/eLife.09560': Counter({'full': 182, 'abstract': 17, 'digest': 0}),
    }
    for key, expected_val in expected.items():
        assert counts[key] == expected_val

# --- V3->V4 Transition

@pytest.mark.django_db
def test_daily_query_results_correct_pre_v4_switch():
    "the results from a query (pre-switch) are calculated correctly"
    from_date = to_date = core.SITE_SWITCH - timedelta(days=1)
    fixture = base.fixture_path('views-2016-02-08.json')
    table_id = ''

    with patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture):
        counts = core.article_views(table_id, from_date, to_date, cached=True)

    expected = {
        '10.7554/eLife.10778': Counter({'full': 119, 'abstract': 10, 'digest': 1}),
        '10.7554/eLife.10509': Counter({'full': 11, 'abstract': 2, 'digest': 0}),
        '10.7554/eLife.09560': Counter({'full': 182, 'abstract': 17, 'digest': 0}),
    }
    for key, expected_val in expected.items():
        assert expected_val == counts[key]

@pytest.mark.django_db
def test_daily_query_results_correct_post_switch():
    "the results from a query (post-switch) are calculated correctly"
    from_date = to_date = core.SITE_SWITCH + timedelta(days=1) # day after
    fixture = base.fixture_path('views-2016-02-10.json')
    table_id = ''
    with patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture):
        counts = core.article_views(table_id, from_date, to_date, cached=True)

    expected = {
        '10.7554/eLife.10518': Counter({'abstract': 0, 'digest': 1, 'full': 4}),
        '10.7554/eLife.10921': Counter({'abstract': 0, 'digest': 2, 'full': 153}),
        '10.7554/eLife.12620': Counter({'abstract': 29, 'digest': 4, 'full': 2053}),
    }
    for key, expected_val in expected.items():
        assert expected_val == counts[key]

# --- V4

@pytest.mark.django_db
def test_elife_v4_excludes_bad_paths():
    fixture_path = base.fixture_path('2017-10-01_2017-10-31.json')
    fixture = json.load(open(fixture_path, 'r'))

    # this fixture has a number of bad paths:
    bad_eggs = [
        ['/articles/004071', '1'],
        ['/articles/121771', '1'],
        ['/articles/2212815887', '1'],
        ['/articles/292222222222222222222222222222222222222222222222222222222222222', '1'],
        ['/articles/2922222222222222222222222222222222222222222222222222222222222229999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999', '2'],
        ['/articles/305610', '1'],
    ]

    from_dt, to_dt = datetime(2017, 10, 1), datetime(2017, 10, 31)
    with patch('article_metrics.ga_metrics.core.query_ga_write_results', return_value=(fixture, fixture_path)):
        with patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture_path):
            results = core.article_views('0xdeadbeef', from_dt, to_dt, cached=False, only_cached=False)
            # total raw results = 4501
            # after filtering bad eggs and aggregation: 4491
            expected = 4491
            assert expected == len(results)

    final_doi_list = list(results.values())
    for path in dict(bad_eggs).values():
        doi = utils.pad_msid(path.rsplit('/', 1)[-1])
        assert doi not in final_doi_list

# --- V5. era is the same as v4, except /executable is added to list of article paths to include.

@pytest.mark.django_db
def test_v5_daily():
    "the daily `/article/123` and `/article/123/executable` sums add up"
    fixture_path = base.fixture_path('v5--views--2020-02-22.json')
    fixture = json.load(open(fixture_path, 'r'))

    from_dt = to_dt = datetime(2020, 2, 22) # daily
    with patch('article_metrics.ga_metrics.core.query_ga_write_results', return_value=(fixture, fixture_path)):
        with patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture_path):
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

            assert expected_total_results == len(results)
            assert expected_total == elife_v1.count_counter_list(results.values())
            for msid, expected_count in expected_sample.items():
                assert expected_count == results[utils.msid2doi(msid)]

@pytest.mark.django_db
def test_v5_monthly():
    "the monthly `/article/123` and `/article/123/executable` sums add up"
    fixture_path = base.fixture_path('v5--views--2020-03-01_2020-03-31.json')
    fixture = json.load(open(fixture_path, 'r'))

    from_dt, to_dt = datetime(2020, 3, 1), datetime(2020, 3, 31) # monthly
    with patch('article_metrics.ga_metrics.core.query_ga_write_results', return_value=(fixture, fixture_path)):
        with patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture_path):
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

            assert expected_total_results == len(results)
            assert expected_total == elife_v1.count_counter_list(results.values())
            for msid, expected_count in expected_sample.items():
                assert expected_count == results[utils.msid2doi(msid)]

# -- V6. era is the same as v5, except paths containing certain url parameters are included.

@pytest.mark.django_db
def test_v6_daily():
    fixture_path = base.fixture_path('v6--views--2021-11-30.json')
    fixture = json.load(open(fixture_path, 'r'))

    from_dt = to_dt = datetime(2021, 12, 1) # daily
    with patch('article_metrics.ga_metrics.core.query_ga_write_results', return_value=(fixture, fixture_path)):
        with patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture_path):
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

            assert expected_num_results == len(results)
            assert expected_total == elife_v1.count_counter_list(results.values())
            for msid, expected_count in expected_sample:
                assert expected_count == results[utils.msid2doi(msid)]

@pytest.mark.django_db
def test_v6_monthly():
    fixture_path = base.fixture_path('v6--views--2021-11-01_2021-11-30.json')
    fixture = json.load(open(fixture_path, 'r'))

    # it's a 2021-11 fixture but we'll use 2021-12 dates so that the v6 module is picked.
    from_dt, to_dt = datetime(2021, 12, 1), datetime(2021, 12, 31) # monthly
    with patch('article_metrics.ga_metrics.core.query_ga_write_results', return_value=(fixture, fixture_path)):
        with patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture_path):
            ga_table_id = '0xdeadbeef'
            results = core.article_views(ga_table_id, from_dt, to_dt, cached=False, only_cached=False)
            # lsh@2023-02-17: regular expression changed. msids now go to 6 digits and anything longer is excluded.
            # "/articles/058355" is now being counted
            # "/articles/5708990" is now being excluded and not counted as "570899"
            #expected_num_results = 11738
            #expected_total = Counter(full=712582, abstract=0, digest=0)
            expected_num_results = 11739
            expected_total = Counter(full=712581, abstract=0, digest=0)

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

            assert expected_num_results == len(results)
            assert expected_total == elife_v1.count_counter_list(results.values())
            for msid, expected_count in expected_sample:
                assert expected_count == results[utils.msid2doi(msid)]

# --- V7. era is the switch from GA3 to GA4

@pytest.mark.django_db
def test_v7_daily_views():
    table_id = ''
    from_dt = to_dt = core.GA4_SWITCH
    fixture_path = base.fixture_path('v7--views--2022-12-01.json')
    fixture = json.load(open(fixture_path, 'r'))
    with patch('article_metrics.ga_metrics.core.query_ga_write_results_v2', return_value=(fixture, fixture_path)):
        with patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture_path):
            results = core.article_views(table_id, from_dt, to_dt, cached=False, only_cached=False)

    expected_num_rows = 7890
    expected_total = Counter(full=32877, abstract=0, digest=0)

    # representative sample of `/article` and `/article/executable`, /article?foo=...
    expected_sample = [
        (83292, Counter(full=761, abstract=0, digest=0)),
        (83071, Counter(full=652, abstract=0, digest=0)),
        (10989, Counter(full=24, abstract=0, digest=0)),
        # 11 regular, 1 /executable
        (61523, Counter(full=11 + 1, abstract=0, digest=0))
    ]

    assert expected_num_rows == len(results)
    assert expected_total == elife_v1.count_counter_list(results.values())
    for msid, expected_count in expected_sample:
        assert expected_count == results[utils.msid2doi(msid)]

@pytest.mark.django_db
def test_v7_monthly_views():
    table_id = ''
    one_month = timedelta(days=31)
    from_dt, to_dt = ga_utils.month_min_max(core.GA4_SWITCH + one_month)
    fixture_path = base.fixture_path('v7--views--2022-11-01_2022-11-30.json')
    fixture = json.load(open(fixture_path, 'r'))
    with patch('article_metrics.ga_metrics.core.query_ga_write_results_v2', return_value=(fixture, fixture_path)):
        with patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture_path):
            results = core.article_views(table_id, from_dt, to_dt, cached=False, only_cached=False)

    expected_num_rows = 9952
    expected_total = Counter(full=772733, abstract=0, digest=0)

    # representative sample of `/article` and `/article/executable`, /article?foo=...
    expected_sample = [
        (83292, Counter(full=2518, abstract=0, digest=0)),
        (83071, Counter(full=3186, abstract=0, digest=0)),
        (10989, Counter(full=409, abstract=0, digest=0)),
        # 81 regular, 22 executable
        (61523, Counter(full=81 + 22, abstract=0, digest=0)),
        # 20 regular, 31 executable
        (30274, Counter(full=20 + 31, abstract=0, digest=0))
    ]

    assert expected_num_rows == len(results)
    assert expected_total == elife_v1.count_counter_list(results.values())
    for msid, expected_count in expected_sample:
        assert expected_count == results[utils.msid2doi(msid)]

@pytest.mark.django_db
def test_v7_daily_downloads():
    table_id = ''
    from_dt = to_dt = core.GA4_SWITCH
    fixture_path = base.fixture_path('v7--downloads--2022-12-01.json')
    fixture = json.load(open(fixture_path, 'r'))
    with patch('article_metrics.ga_metrics.core.query_ga_write_results_v2', return_value=(fixture, fixture_path)):
        with patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture_path):
            results = core.article_downloads(table_id, from_dt, to_dt, cached=False, only_cached=False)

    expected_num_rows = 1114
    expected_total = 2527

    # representative sample
    expected_sample = [
        (83292, 45),
        (83071, 48),
        (10989, 2),
        (61562, 1),
        (30294, 3),
    ]

    assert expected_num_rows == len(results)
    assert expected_total == sum(results.values())
    for msid, expected_count in expected_sample:
        doi = utils.msid2doi(msid)
        assert expected_count == results[doi]

@pytest.mark.django_db
def test_v7_monthly_downloads():
    table_id = ''
    one_month = timedelta(days=31) # an overlap for month ranges will use elife-v6.
    from_dt, to_dt = ga_utils.month_min_max(core.GA4_SWITCH + one_month)
    fixture_path = base.fixture_path('v7--downloads--2022-11-01_2022-11-30.json')
    fixture = json.load(open(fixture_path, 'r'))
    with patch('article_metrics.ga_metrics.core.query_ga_write_results_v2', return_value=(fixture, fixture_path)):
        with patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture_path):
            results = core.article_downloads(table_id, from_dt, to_dt, cached=False, only_cached=False)

    expected_num_rows = 10025
    expected_total = 69818

    # representative sample
    expected_sample = [
        (83292, 230),
        (83071, 240),
        (10989, 37),
        (61523, 14),
        (30278, 7),
    ]

    assert expected_num_rows == len(results)
    assert expected_total == sum(results.values())
    for msid, expected_count in expected_sample:
        doi = utils.msid2doi(msid)
        assert expected_count == results[doi]

def test_v8_daily_downloads():
    table_id = ''
    from_dt = to_dt = core.GA4_DOWNLOADS_SWITCH
    fixture_path = base.fixture_path('v8--downloads--2023-08-13.json')
    fixture = json.load(open(fixture_path, 'r'))
    with patch('article_metrics.ga_metrics.core.query_ga_write_results_v2', return_value=(fixture, fixture_path)):
        with patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture_path):
            results = core.article_downloads(table_id, from_dt, to_dt, cached=False, only_cached=False)

    expected_num_rows = 496 # 497 # we have a duplicate event for 7939 after msid normalisation
    expected_total = 609
    assert expected_num_rows == len(results)
    assert expected_total == sum(results.values())

    # representative sample
    expected_sample = [
        (7939, 2),
        (86090, 11),
        (58039, 1),
    ]

    for msid, expected_count in expected_sample:
        doi = utils.msid2doi(msid)
        assert expected_count == results[doi]

def test_v8_monthly_downloads():
    table_id = ''
    one_month = timedelta(days=31) # an overlap for month ranges will use elife-v6.
    from_dt, to_dt = ga_utils.month_min_max(core.GA4_DOWNLOADS_SWITCH + one_month)
    fixture_path = base.fixture_path('v8--downloads--2023-07-01_2023-07-31.json')
    fixture = json.load(open(fixture_path, 'r'))
    with patch('article_metrics.ga_metrics.core.query_ga_write_results_v2', return_value=(fixture, fixture_path)):
        with patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture_path):
            results = core.article_downloads(table_id, from_dt, to_dt, cached=False, only_cached=False)

    expected_num_rows = 414
    expected_total = 1291
    assert expected_num_rows == len(results)
    assert expected_total == sum(results.values())

    # representative sample
    expected_sample = [
        (3080, 8),
        (2872, 14),
        (2758, 23),
        (1684, 1),
    ]

    for msid, expected_count in expected_sample:
        doi = utils.msid2doi(msid)
        assert expected_count == results[doi]
