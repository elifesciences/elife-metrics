from . import base
import os
from article_metrics import utils
from article_metrics.utils import tod, lmap, first
from metrics import logic, models, history
from datetime import date, timedelta
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
        start = date(year=2017, month=6, day=3) # non-minimum value to catch any minimising/maximising
        end = date(year=2017, month=12, day=25) # non-maximum value
        result0 = date(year=2017, month=7, day=31) # end of first two-month chunk

        frame_query_list = logic.build_ga_query(models.EVENT, start, end)

        frame, ql = frame_query_list[0]

        # 4 queries over 6 months:
        #  2017-6, 2017-7
        #  2017-8, 2017-9
        #  2017-10, 2017-11
        #  2017-12
        self.assertEqual(len(ql), 4)

        # the range is correct
        self.assertEqual(ql[0]['start_date'], start)
        self.assertEqual(ql[-1]['end_date'], end)
        # the first chunk is correct
        self.assertEqual(ql[0]['end_date'], result0)

    def test_build_ga_query_single(self):
        "a query for a single day (no month range) is possible"
        start = end = date(year=2018, month=1, day=1)
        frame_query_list = logic.build_ga_query(models.EVENT, start, end)
        frame, ql = frame_query_list[0]

        # one result. each result is a (frame, query_list) pair
        self.assertEqual(len(frame_query_list), 1)
        self.assertEqual(ql[0]['start_date'], start)
        self.assertEqual(ql[0]['end_date'], end)

    def test_build_ga_query_multiple_frames(self):
        "a query for a date range that overlaps epochs generates the correct queries"
        midJan18 = date(year=2018, month=1, day=15)
        midDec17 = date(year=2017, month=12, day=15)
        one_day = timedelta(days=1)
        to_day = date.today()

        history_data = {
            'frames': [
                {'id': 2,
                 'starts': midJan18,
                 'ends': None,
                 'prefix': '/new/pants'},
                {'id': 1,
                 'starts': midDec17,
                 'ends': midJan18 - one_day,
                 'prefix': '/old/pants'}
            ]
        }

        starts = midDec17
        ends = midJan18 # ending on a frame boundary is unreasonable but entirely possible

        ql = logic.build_ga_query__frame_month_range(models.EVENT, starts, ends, history_data)

        frame_list = lmap(first, ql) # just the frame and not the query for now

        # frames are not modified after being validated/coerced
        expected_frames = [
            {'id': '1', 'starts': midDec17, 'ends': midJan18 - one_day, 'prefix': '/old/pants'},
            {'id': '2', 'starts': midJan18, 'ends': to_day, 'prefix': '/new/pants'}
        ]
        self.assertEqual(frame_list, expected_frames)

        # month ranges for a frame *are* truncated/capped to align with explicit start/end dates
        month_lists = [ml for f, ml in ql]

        expected_month_lists = [
            # frame 1
            [(midDec17, date(2017, 12, 31)), (date(2018, 1, 1), midJan18 - one_day)],
            # frame 2
            [(midJan18, midJan18)]
        ]
        self.assertEqual(month_lists, expected_month_lists)

    #
    #
    #

    def test_query_ga(self):
        "a standard response from GA is handled as expected, a dump file is created etc"
        jan18 = date(year=2018, month=1, day=1)
        feb18 = date(year=2018, month=2, day=28)

        frame_query_list = logic.build_ga_query(models.EVENT, jan18, feb18)
        frame, query_list = frame_query_list[0]
        query = query_list[0]

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

    def test_ga_query(self):
        "if we have a query for a specific start/end date, those dates are not maximised/minimised to month borders"
        midJan18 = date(2018, 1, 15)
        midMar18 = date(2018, 3, 15)
        frame_query_list = logic.build_ga_query(models.EVENT, midJan18, midMar18)
        frame, ql = frame_query_list[0]
        self.assertEqual(ql[0]['start_date'], midJan18)
        self.assertEqual(ql[-1]['end_date'], midMar18)

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
            (8, {'views': 4, 'identifier': '', 'date': date(2018, 1, 16)}),
            (32, {'identifier': '843d8750', 'views': 245, 'date': date(2018, 1, 12)}),
            (35, {'views': 437, 'identifier': '843d8750', 'date': date(2018, 1, 15)}),
            (114, {'views': 12, 'identifier': 'c40798c3', 'date': date(2018, 1, 11)})
        ]
        for idx, expected_row in expected:
            self.assertEqual(processed_results[idx], expected_row)

    def test_process_response_special_processor(self):
        "special handling of results may be necessary for specific time frames"
        self.fail()

    def test_process_response_no_results(self):
        "a response with no results issues a warning but otherwise doesn't break"
        frame = {'id': '2', 'prefix': '/events'}
        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events-frame2.json'), 'r'))
        del fixture['rows']
        with patch('metrics.logic.LOG') as mock:
            processed_results = logic.process_response(models.EVENT, frame, fixture)
            self.assertEqual(mock.warn.call_count, 1)
            expected_results = []
            self.assertEqual(processed_results, expected_results)

    def test_process_response_bad_apples(self):
        "bad rows in response are discarded"
        frame = {'id': '2', 'prefix': '/events'}
        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events-frame2.json'), 'r'))

        apple1 = 1
        fixture['rows'][apple1] = [None, None, None] # it's a triple but quite useless (ValueError)
        apple2 = 7
        fixture['rows'][apple2] = 'how you like them apples?' # unhandled (BaseException)

        with patch('metrics.logic.LOG') as mock:
            processed_results = logic.process_response(models.EVENT, frame, fixture) # kaboom
            expected_results = 122 - 2 # total non-aggregated results minus bad apples
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

    def test_update_ptype(self):
        self.assertEqual(models.Page.objects.count(), 0)
        self.assertEqual(models.PageType.objects.count(), 0)
        self.assertEqual(models.PageCount.objects.count(), 0)

        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events-frame2.json'), 'r'))

        frame = {'id': '2', 'prefix': '/events'}
        frame_query_list = [(frame, [{}])]
        with patch('metrics.logic.build_ga_query', return_value=frame_query_list):
            with patch('metrics.logic.query_ga', return_value=fixture):
                logic.update_ptype(models.EVENT)

        self.assertEqual(models.Page.objects.count(), 11)
        self.assertEqual(models.PageType.objects.count(), 1) # 'event'
        # not the same as len(fixture.rows) because of aggregation
        self.assertEqual(models.PageCount.objects.count(), 115)

class Four(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_generic_query_pattern(self):
        "dead simple usecase when you want full control of query to GA"
        frame = {'pattern': '/pants'} # this would be shooting yourself in the foot however
        expected = [{'filters': '/pants'}] # a list of GA queries typically, but we can get away with the bare minimum
        self.assertEqual(logic.generic_query_processor('', frame, [{}]), expected)

    def test_generic_query_prefix(self):
        "a simple 'prefix' and nothing else will get you a basic 'landing page and sub-contents' type query"
        prefix = '/pants'
        frame = {'prefix': prefix}
        expected = [{'filters': logic.generic_ga_filter('/pants')}] # ll: "ga:pagePath=~^{prefix}$,ga:pagePath=~^{prefix}/.*$"
        self.assertEqual(logic.generic_query_processor('', frame, [{}]), expected)

    def test_generic_query_prefix_list(self):
        "a 'prefix' and a list of subpaths will get you a landing page and enumerated sub-paths query"
        prefix = '/pants'
        frame = {'prefix': prefix, 'path-list': ['foo', 'bar', 'baz']}
        expected = [{'filters': "ga:pagePath=~^/pants$,ga:pagePath=~^/pants/foo$,ga:pagePath=~^/pants/bar$,ga:pagePath=~^/pants/baz$"}]
        self.assertEqual(logic.generic_query_processor('', frame, [{}]), expected)

    def test_generic_query_prefix_list__collections(self):
        "essentially a duplicate test, but using actual data"
        collection = history.ptype_history(models.COLLECTION)
        frame = collection['frames'][0]
        # I do not endorse this official-but-awful method of string concatenation
        expected = 'ga:pagePath=~^/collections$' \
                   ',ga:pagePath=~^/collections/chemical-biology$' \
                   ',ga:pagePath=~^/collections/tropical-disease$' \
                   ',ga:pagePath=~^/collections/paleontology$' \
                   ',ga:pagePath=~^/collections/human-genetics$' \
                   ',ga:pagePath=~^/collections/natural-history-model-organisms$' \
                   ',ga:pagePath=~^/collections/reproducibility-project-cancer-biology$' \
                   ',ga:pagePath=~^/collections/plain-language-summaries$'
        expected = [{'filters': expected}]
        actual = logic.generic_query_processor(models.COLLECTION, frame, [{}])
        self.assertEqual(actual, expected)
