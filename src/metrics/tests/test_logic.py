from . import base
import os
from article_metrics import utils
from article_metrics.utils import tod, lmap, first, second, subdict
from metrics import logic, models, history
from datetime import date, timedelta
from unittest.mock import patch
from collections import OrderedDict
from django.db.models import Sum
from django.test import override_settings
import json

class One(base.BaseCase):
    def test_no_nothing(self):
        "logic.page_views returns None when Page not found"
        expected_result = None
        pid, ptype = 'foo', 'event'
        self.assertEqual(logic.page_views(pid, ptype), expected_result)

    def test_bad_metrics(self):
        "logic.page_views throws ValueError when we give it gibberish"
        etc = self
        for bad_pid in [1, {}, [], etc]:
            for bad_ptype in [1, 'foo', {}, [], etc]:
                for bad_period in [1, 'foo', {}, [], etc]:
                    # TODO: revisit this test, why isn't bad_period being used?
                    self.assertRaises(ValueError, logic.page_views, bad_pid, bad_ptype)

    def test_daily_metrics(self):
        "logic.page_views returns the sum of all daily hits and a chop'able queryset"
        fixture = [
            ('pants', 'event', '2016-01-01', 1),
            ('pants', 'event', '2016-01-02', 2),
            ('pants', 'event', '2016-01-03', 4),
            ('pants', 'event', '2016-01-04', 8)

            # it's obvious the pants event is exponentially popular
        ]
        base.insert_metrics(fixture)

        expected_sum = 15
        total, qobj = logic.page_views('pants', 'event', logic.DAY)
        self.assertEqual(total, expected_sum)
        self.assertEqual(qobj.count(), len(fixture))

    def test_monthly_metrics(self):
        "logic.page_views returns the sum of all monthly hits (same as sum of all daily hits) and a chop'able queryset"
        fixture = [
            ('pants', 'event', '2016-01-30', 1),
            ('pants', 'event', '2016-01-31', 2),
            ('pants', 'event', '2016-02-01', 3),
        ]
        base.insert_metrics(fixture)

        expected_sum = 6
        expected_result_count = 2 # results span two months
        total, qobj = logic.page_views('pants', 'event', logic.MONTH)
        self.assertEqual(total, expected_sum)
        self.assertEqual(qobj.count(), expected_result_count)

    def test_process_results_prefixed_path(self):
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
            with self.subTest():
                self.assertEqual(logic.process_prefixed_path('/pants', given), expected)

    def test_process_results_mapped_path(self):
        "a mapping of path->identifier will return the identifier"
        mapping = {
            '/pants/foo': 'bar',
            '/party/baz': 'bar',
        }
        cases = [
            "/pants/foo",
            "/party/baz",
            "https://sub.example.org/pants/foo",
            "/pants/foo?bar=baz",
            "/pants/foo?bar=baz&bup=",
            "/pants/foo#bar",
            "/pants/foo#bar?baz=bup",
        ]
        expected = 'bar'
        for given in cases:
            with self.subTest():
                self.assertEqual(logic.process_mapped_path(mapping, given), expected, "failed on %s" % given)

class Two(base.BaseCase):
    def setUp(self):
        self.tmpdir, self.rm_tmpdir = utils.tempdir()

    def tearDown(self):
        self.rm_tmpdir()

    def test_interesting_frames(self):
        one_day = timedelta(days=1)
        one_moonth = timedelta(days=28)
        a = date(year=2017, month=1, day=1)
        b = a + one_moonth
        c = b + one_moonth
        d = c + one_moonth
        e = d + one_moonth
        f = e + one_moonth

        starts, ends = b + one_day, e - one_day

        frames = [
            {'starts': a, 'ends': b}, # outside of scope
            {'starts': b, 'ends': c}, # partially in scope
            {'starts': c, 'ends': d}, # completely in scope
            {'starts': d, 'ends': e}, # partially in scope
            {'starts': e, 'ends': f}, # outside of scope
        ]

        expected_frames = [
            {'starts': b, 'ends': c}, # partially in scope
            {'starts': c, 'ends': d}, # completely in scope
            {'starts': d, 'ends': e}, # partially in scope
        ]
        self.assertEqual(logic.interesting_frames(starts, ends, frames), expected_frames)

    def test_build_ga_query(self):
        "the list of queries returned has the right shape"
        start = date(year=2017, month=6, day=3) # non-minimum value to catch any minimising/maximising
        end = date(year=2017, month=12, day=25) # non-maximum value
        frame_query_list = logic.build_ga_query(models.EVENT, start, end)
        frame, query = frame_query_list[0]
        self.assertEqual(query['start_date'], start)
        self.assertEqual(query['end_date'], end)

    def test_build_ga_query_single(self):
        "a query for a single day is possible"
        start = end = date(year=2018, month=1, day=1)
        frame_query_list = logic.build_ga_query(models.EVENT, start, end)
        frame, query = frame_query_list[0]

        # one result. each result is a (frame, query_list) pair
        self.assertEqual(len(frame_query_list), 1)
        self.assertEqual(query['start_date'], start)
        self.assertEqual(query['end_date'], end)

    def test_build_ga_query_multiple_frames(self):
        "a query for a date range that overlaps epochs generates the correct queries"
        midJan18 = date(year=2018, month=1, day=15)
        midDec17 = date(year=2017, month=12, day=15)
        one_day = timedelta(days=1)
        two_days = timedelta(days=2)
        to_day = date.today()

        history_data = {
            'frames': [
                {'id': 2,
                 'ends': None,
                 'starts': midJan18,
                 'pattern': '/new/pants'},
                {'id': 1,
                 'ends': midJan18 - one_day,
                 'starts': midDec17,
                 'pattern': '/old/pants'}
            ]
        }
        # `validate` does more than validation, it also sorts frames and fills in empty dates.
        # `history.type_object` is the schema for the 'frames' data with a ptype dict.
        history_data = history.type_object.validate(history_data)

        # starts/ends just outside frame boundaries
        starts = midDec17 - two_days
        ends = midJan18 + two_days

        with patch('metrics.history.ptype_history', return_value=history_data):
            ql = logic.build_ga_query(models.EVENT, starts, ends)

        frame_list = lmap(first, ql) # just the frames and not the queries for now

        # frames are not modified after being validated/coerced
        expected_frames = [
            {'id': '1', 'starts': midDec17, 'ends': midJan18 - one_day, 'pattern': '/old/pants'},
            {'id': '2', 'starts': midJan18, 'ends': to_day, 'pattern': '/new/pants'}
        ]
        self.assertEqual(frame_list, expected_frames)

        expected_query_dates = [
            # first query: starts and ends on frame boundaries, ignoring explicit start date
            {'start_date': midDec17, 'end_date': midJan18 - one_day, 'pattern': '/old/pants'}, # id=1

            # second query: starts on frame boundary and ends on explicit end date
            {'start_date': midJan18, 'end_date': ends, 'pattern': '/new/pants'}, # id=2
        ]
        for expected, query in zip(expected_query_dates, lmap(second, ql)):
            subquery = subdict(query, ['start_date', 'end_date', 'filters'])
            utils.renkeys(subquery, [('filters', 'pattern')])
            self.assertEqual(subquery, expected)

    #
    #
    #

    def test_query_ga_pagination(self):
        "paginated GA queries behave as expected"
        total_results = 8
        query = {
            'start_date': '2012-01-01',
            'end_date': '2013-01-01',
            'filters': 'ga:pagePath==/pants',
        }
        # https://developers.google.com/analytics/devguides/reporting/core/v3/reference#data_response
        response_template = {
            'totalResults': total_results,
            'rows': [], # doesn't matter, rows are not consulted
            'itemsPerPage': None, # set during test
            'query': query
        }
        cases = [
            # items per-page, expected pages
            (1, 8),
            (2, 4),
            (3, 3),
            (4, 2),
            (5, 2),
            (6, 2),
            (7, 2),
            (8, 1),
            (9, 1),
        ]
        for items_pp, expected_pages in cases:
            response_list = [response_template] * expected_pages
            with patch('article_metrics.ga_metrics.core._query_ga', side_effect=response_list) as mock:
                response = logic.query_ga(models.EVENT, query, items_pp)
                self.assertEqual(response['totalPages'], expected_pages)
                self.assertEqual(mock.call_count, expected_pages)

    def test_query_ga_pagination_bad_pp(self):
        cases = [0, 10001, 99999999, "", "pants", {}, []]
        for case in cases:
            self.assertRaises(AssertionError, logic.query_ga, models.EVENT, {}, case)

    @override_settings(TESTING=False) # urgh, caching in elife-metrics needs an overhaul
    def test_query_ga(self):
        "a standard response from GA is handled as expected, a dump file is created etc"
        jan18 = date(year=2018, month=1, day=1)
        feb18 = date(year=2018, month=2, day=28)

        frame_query_list = logic.build_ga_query(models.EVENT, jan18, feb18)
        frame, query = frame_query_list[0]

        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events-frame2.json'), 'r'))
        dumpfile = os.path.join(self.tmpdir, "pants.json")
        with patch('article_metrics.ga_metrics.core.output_path', return_value=dumpfile):
            with patch('article_metrics.ga_metrics.core.query_ga', return_value=fixture):
                result = logic.query_ga(models.EVENT, query)
                self.assertEqual(result, fixture)
                # ensure the dump file was written for debugging/loading later
                contents = os.listdir(self.tmpdir)
                self.assertEqual(len(contents), 1)
                self.assertEqual(json.load(open(dumpfile, 'r')), fixture)

    #
    #
    #

    def test_process_response_generic_processor(self):
        "response is processed predictably, views are ints, dates are dates, results retain their order, etc"
        frame = {'id': '2', 'prefix': '/events'}
        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events-frame2.json'), 'r'))

        processed_results = logic.process_response(models.EVENT, frame, fixture)

        # list index, expected row
        expected = [
            (10, {'views': 7, 'identifier': '', 'date': date(2018, 1, 16)}),
            (54, {'identifier': '843d8750', 'views': 247, 'date': date(2018, 1, 12)}),
            (57, {'views': 446, 'identifier': '843d8750', 'date': date(2018, 1, 15)}),
            (121, {'views': 2, 'identifier': 'c40798c3', 'date': date(2018, 1, 11)})
        ]
        for idx, expected_row in expected:
            self.assertEqual(expected_row, processed_results[idx])

    def test_process_response_no_results(self):
        "a response with no results issues a warning but otherwise doesn't break"
        frame = {'id': '2', 'prefix': '/events'}
        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events-frame2.json'), 'r'))
        del fixture['rows']
        with patch('metrics.logic.LOG') as mock:
            processed_results = logic.process_response(models.EVENT, frame, fixture)
            self.assertEqual(mock.warning.call_count, 1)
            expected_results = []
            self.assertEqual(processed_results, expected_results)

    def test_process_response_bad_apples(self):
        "bad rows in response are discarded"
        frame = {'id': '2', 'prefix': '/events'}
        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events-frame2.json'), 'r'))

        apple1 = 1
        fixture['rows'][apple1] = [None, None, None] # it's a triple but quite useless (ValueError)
        apple2 = 7
        fixture['rows'][apple2] = 'how you like dem apples?' # unhandled (BaseException)

        with patch('metrics.logic.LOG') as mock:
            processed_results = logic.process_response(models.EVENT, frame, fixture) # kaboom
            expected_results = 147 - 2 # total non-aggregated results minus bad apples
            self.assertEqual(len(processed_results), expected_results)
            self.assertEqual(mock.exception.call_count, 1) # one unhandled error
            self.assertEqual(mock.info.call_count, 1) # one handled error


class Three(base.BaseCase):

    def test_aggregate(self):
        normalised_rows = logic.asmaps([
            ("/events/foo", tod("2018-01-01"), 1),
            ("/events/foo", tod("2018-01-02"), 2),

            ("/events/foo", tod("2018-01-03"), 2),
            ("/events/bar", tod("2018-01-03"), 1),
            ("/events/foo", tod("2018-01-03"), 2),
        ])

        expected_result = logic.asmaps([
            ("/events/foo", tod("2018-01-01"), 1),
            ("/events/foo", tod("2018-01-02"), 2),
            ("/events/foo", tod("2018-01-03"), 4), # aggregated
            ("/events/bar", tod("2018-01-03"), 1)
        ])
        self.assertCountEqual(logic.aggregate(normalised_rows), expected_result)

    def test_insert(self):
        self.assertEqual(models.Page.objects.count(), 0)
        self.assertEqual(models.PageType.objects.count(), 0)
        self.assertEqual(models.PageCount.objects.count(), 0)

        aggregated_rows = logic.asmaps([
            ("/events/foo", tod("2018-01-01"), 1),
            ("/events/foo", tod("2018-01-02"), 2),
            ("/events/foo", tod("2018-01-03"), 4),
            ("/events/bar", tod("2018-01-03"), 1)
        ])
        results = logic.update_page_counts(models.EVENT, aggregated_rows)
        self.assertEqual(len(results), len(aggregated_rows))

        self.assertEqual(models.PageType.objects.count(), 1)
        self.assertEqual(models.Page.objects.count(), 2)
        self.assertEqual(models.PageCount.objects.count(), 4)

    def test_double_insert(self):
        aggregated_rows = logic.asmaps([
            ("/events/foo", tod("2018-01-01"), 1),
            ("/events/foo", tod("2018-01-02"), 2),
            ("/events/foo", tod("2018-01-03"), 4),
            ("/events/bar", tod("2018-01-03"), 1)
        ])
        results = logic.update_page_counts(models.EVENT, aggregated_rows)
        self.assertEqual(len(results), len(aggregated_rows))
        self.assertEqual(models.PageType.objects.count(), 1)
        self.assertEqual(models.Page.objects.count(), 2)
        self.assertEqual(models.PageCount.objects.count(), 4)
        expected_total = 8
        actual_total = lambda: models.PageCount.objects.aggregate(total=Sum('views'))['total']
        self.assertEqual(expected_total, actual_total())

        # increase the view count, insert again.
        aggregated_rows = logic.asmaps([
            ("/events/foo", tod("2018-01-01"), 2),
            ("/events/foo", tod("2018-01-02"), 4),
            ("/events/foo", tod("2018-01-03"), 8),
            ("/events/bar", tod("2018-01-03"), 2)
        ])
        results = logic.update_page_counts(models.EVENT, aggregated_rows)
        self.assertEqual(len(results), len(aggregated_rows))

        # these numbers should have stayed the same
        self.assertEqual(models.PageType.objects.count(), 1)
        self.assertEqual(models.Page.objects.count(), 2)
        self.assertEqual(models.PageCount.objects.count(), 4)

        # but this should reflect the new total
        expected_total = 16
        self.assertEqual(expected_total, actual_total())

    def test_update_ptype(self):
        "`update_ptype` convenience function behaves as expected"
        self.assertEqual(models.Page.objects.count(), 0)
        self.assertEqual(models.PageType.objects.count(), 0)
        self.assertEqual(models.PageCount.objects.count(), 0)

        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events-frame2.json'), 'r'))

        frame = {'id': '2', 'prefix': '/events'}
        frame_query_list = [(frame, [{}])]
        with patch('metrics.logic.build_ga_query', return_value=frame_query_list):
            with patch('metrics.logic.query_ga', return_value=fixture):
                logic.update_ptype(models.EVENT)

        self.assertEqual(models.Page.objects.count(), 13)
        self.assertEqual(models.PageType.objects.count(), 1) # 'event'
        # not the same as len(fixture.rows) because of aggregation
        self.assertEqual(models.PageCount.objects.count(), 138)

class Five(base.BaseCase):
    def test_parse_redirect_map(self):
        frame = {
            'redirect-prefix': '/inside-elife',
        }
        contents = '''
            '/new-study-1-in-4-sharks-and-rays-threatened-with-extinction-national-geographic' '/inside-elife/fbbb5b76';
            '/u-k-panel-backs-open-access-for-all-publicly-funded-research-papers' '/inside-elife/fbbcdd2b';
            '/elife-news/uk-panel-backs-open-access-all-publicly-funded-research-papers' '/inside-elife/fbbcdd2b';
        '''
        results = logic.parse_map_file(frame, contents)
        expected = OrderedDict([
            ('/new-study-1-in-4-sharks-and-rays-threatened-with-extinction-national-geographic', 'fbbb5b76'),
            ('/u-k-panel-backs-open-access-for-all-publicly-funded-research-papers', 'fbbcdd2b'),
            ('/elife-news/uk-panel-backs-open-access-all-publicly-funded-research-papers', 'fbbcdd2b')])
        self.assertEqual(results, expected)
