from . import base
import os
from metrics import utils
from metrics.utils import tod
from nametrics import logic, models
from datetime import date
from unittest.mock import patch
import json

class One(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

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
            ('pants', 'event', '2016-01-31', 1),
            ('pants', 'event', '2016-01-31', 2),
            ('pants', 'event', '2016-02-01', 3),
        ]
        base.insert_metrics(fixture)

        expected_sum = 6
        expected_result_count = 2 # results span two months
        total, qobj = logic.page_views('pants', 'event', logic.MONTH)
        self.assertEqual(total, expected_sum)
        self.assertEqual(qobj.count(), expected_result_count)

    def test_process_path(self):
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
                self.assertEqual(logic.process_path('/pants', given), expected)

class Two(base.BaseCase):
    def setUp(self):
        self.tmpdir, self.rm_tmpdir = utils.tempdir()

    def tearDown(self):
        self.rm_tmpdir()

    def test_build_ga_query(self):
        "the list of queries returned has the right shape"
        jan18 = date(year=2018, month=1, day=3) # non-minimum value to catch any minimising/maximising
        dec18 = date(year=2018, month=12, day=25) # non-maximum value
        feb18 = date(year=2018, month=2, day=28)
        ql = logic.build_ga_query(models.EVENT, jan18, dec18)
        self.assertEqual(len(ql), 6) # 6 * 2 month chunks
        query = 1 # frame = 0
        # the range is correct
        self.assertEqual(ql[0][query]['start_date'], jan18)
        self.assertEqual(ql[-1][query]['end_date'], dec18)
        # the first chunk is correct
        self.assertEqual(ql[0][query]['end_date'], feb18)

    def test_build_ga_query_single(self):
        "a query for a single day (no month range) is possible"
        jan18 = date(year=2018, month=1, day=1)
        ql = logic.build_ga_query(models.EVENT, jan18, jan18) # two start dates...
        query = 1 # frame = 0
        self.assertEqual(len(ql), 1)
        self.assertEqual(ql[0][query]['start_date'], jan18)
        self.assertEqual(ql[0][query]['end_date'], jan18)

    def test_load_ptype_history(self):
        logic.load_ptype_history(models.EVENT)

    def test_load_missing_ptype_history(self):
        self.assertRaises(ValueError, logic.load_ptype_history, "pants")

    def test_query_ga(self):
        "a standard response from GA is handled as expected, a dump file is created etc"
        jan18 = date(year=2018, month=1, day=1)
        feb18 = date(year=2018, month=2, day=28)
        frame, query = logic.build_ga_query(models.EVENT, jan18, feb18)[0]
        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events.json'), 'r'))
        dumpfile = os.path.join(self.tmpdir, "pants.json")
        with patch('metrics.ga_metrics.core.output_path', return_value=dumpfile):
            with patch('metrics.ga_metrics.core.query_ga', return_value=fixture):
                result = logic.query_ga(models.EVENT, query)
                self.assertEqual(result, fixture)
                # ensure the dump file was written for debugging/loading later
                contents = os.listdir(self.tmpdir)
                self.assertEqual(len(contents), 1)
                self.assertEqual(json.load(open(dumpfile, 'r')), fixture)

    def test_ga_query(self):
        "if we have a query for a specific start/end date, those dates are not maximised/minimised to month borders"
        midJan18 = date(2018, 1, 15)
        midMar18 = date(2018, 3, 15)
        ql = logic.build_ga_query(models.EVENT, midJan18, midMar18)
        query = 1 # frame = 0
        self.assertEqual(ql[0][query]['start_date'], midJan18)
        self.assertEqual(ql[-1][query]['end_date'], midMar18)

    def test_process_response(self):
        "response is processed predictably, views are ints, dates are dates, results retain their order, etc"
        frame = {'prefix': '/events'}
        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events.json'), 'r'))

        processed_results = logic.process_response(models.EVENT, frame, fixture)
        # for i, row in enumerate(processed_results):
        #    print(i, row)

        # list index, expected row
        expected = [
            (8, {'views': 4, 'identifier': '', 'date': date(2018, 1, 16)}),
            (32, {'identifier': '843d8750', 'views': 245, 'date': date(2018, 1, 12)}),
            (35, {'views': 437, 'identifier': '843d8750', 'date': date(2018, 1, 15)}),
            (114, {'views': 12, 'identifier': 'c40798c3', 'date': date(2018, 1, 11)})
        ]
        for idx, expected_row in expected:
            self.assertEqual(processed_results[idx], expected_row)

    def test_process_response_no_results(self):
        "a response with no results issues a warning but otherwise doesn't break"
        frame = {'prefix': '/events'}
        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events.json'), 'r'))
        del fixture['rows']
        with patch('nametrics.logic.LOG') as mock:
            processed_results = logic.process_response(models.EVENT, frame, fixture)
            self.assertEqual(mock.warn.call_count, 1)
            expected_results = []
            self.assertEqual(processed_results, expected_results)

    def test_process_response_bad_apples(self):
        "bad rows in response are discarded"
        frame = {'prefix': '/events'}
        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events.json'), 'r'))

        apple1 = 1
        fixture['rows'][apple1] = [None, None, None] # it's a triple but quite useless
        apple2 = 7
        fixture['rows'][apple2] = 'how you like them apples?'

        with patch('nametrics.logic.LOG') as mock:
            processed_results = logic.process_response(models.EVENT, frame, fixture) # kaboom
            expected_results = 122 - 2 # total non-aggregated results minus bad apples
            self.assertEqual(len(processed_results), expected_results)
            self.assertEqual(mock.exception.call_count, 2) # two unhandled errors for two bad apples


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

    def test_update_ptype(self):
        self.assertEqual(models.Page.objects.count(), 0)
        self.assertEqual(models.PageType.objects.count(), 0)
        self.assertEqual(models.PageCount.objects.count(), 0)

        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events.json'), 'r'))

        frame = {'prefix': '/events'}
        with patch('nametrics.logic.build_ga_query', return_value=[[frame, {}]]):
            with patch('nametrics.logic.query_ga', return_value=fixture):
                logic.update_ptype(models.EVENT)

        self.assertEqual(models.Page.objects.count(), 11)
        self.assertEqual(models.PageType.objects.count(), 1) # 'event'
        # not the same as len(fixture.rows) because of aggregation
        self.assertEqual(models.PageCount.objects.count(), 115)
