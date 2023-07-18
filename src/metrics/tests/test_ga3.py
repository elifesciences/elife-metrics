from collections import OrderedDict
from . import base
import os
from article_metrics import utils
from article_metrics.utils import lmap, first, second, subdict, date_today
from metrics import logic, ga3, models, history
from datetime import date, timedelta
from unittest.mock import patch
from django.test import override_settings
import json

class One(base.BaseCase):
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
                self.assertEqual(ga3.process_prefixed_path('/pants', given), expected)

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
                self.assertEqual(ga3.process_mapped_path(mapping, given), expected, "failed on %s" % given)

class Two(base.BaseCase):
    def setUp(self):
        self.tmpdir, self.rm_tmpdir = utils.tempdir()

    def tearDown(self):
        self.rm_tmpdir()

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
        to_day = date_today()

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
            self.assertRaises(AssertionError, ga3.query_ga, models.EVENT, {}, case)

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

    def test_process_response_generic_processor(self):
        "response is processed predictably, views are ints, dates are dates, results retain their order, etc"
        frame = {'id': '2', 'prefix': '/events'}
        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events-frame2.json'), 'r'))

        processed_results = ga3.process_response(models.EVENT, frame, fixture)

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
        with patch('metrics.ga3.LOG') as mock:
            processed_results = ga3.process_response(models.EVENT, frame, fixture)
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

        with patch('metrics.ga3.LOG') as mock:
            processed_results = ga3.process_response(models.EVENT, frame, fixture) # kaboom
            expected_results = 147 - 2 # total non-aggregated results minus bad apples
            self.assertEqual(len(processed_results), expected_results)
            self.assertEqual(mock.exception.call_count, 1) # one unhandled error
            self.assertEqual(mock.info.call_count, 1) # one handled error


class Four(base.BaseCase):
    def test_generic_query_pattern(self):
        "dead simple usecase when you want full control of query to GA"
        frame = {'pattern': '/pants'} # this would be shooting yourself in the foot however
        expected = '/pants' # a list of GA queries typically, but we can get away with the bare minimum
        self.assertEqual(ga3.generic_query_processor(None, frame), expected)

    def test_generic_query_prefix(self):
        "a simple 'prefix' and nothing else will get you a basic 'landing page and sub-contents' type query"
        prefix = '/pants'
        frame = {'prefix': prefix}
        expected = ga3.generic_ga_filter('/pants') # ll: "ga:pagePath=~^{prefix}$,ga:pagePath=~^{prefix}/.*$"
        self.assertEqual(ga3.generic_query_processor(None, frame), expected)

    def test_generic_query_prefix_list(self):
        "a 'prefix' and a list of subpaths will get you a landing page and enumerated sub-paths query"
        prefix = '/pants'
        frame = {'prefix': prefix, 'path-list': ['foo', 'bar', 'baz']}
        expected = "ga:pagePath=~^/pants$,ga:pagePath=~^/pants/foo$,ga:pagePath=~^/pants/bar$,ga:pagePath=~^/pants/baz$"
        self.assertEqual(ga3.generic_query_processor(None, frame), expected)

    def test_generic_query_prefix_list__collections(self):
        "essentially a duplicate test, but using actual data"
        collection = history.ptype_history(models.COLLECTION)
        frame = collection['frames'][0]
        # note: I do not endorse this official-but-awful method of string concatenation
        expected = 'ga:pagePath=~^/collections/chemical-biology$' \
                   ',ga:pagePath=~^/collections/tropical-disease$' \
                   ',ga:pagePath=~^/collections/paleontology$' \
                   ',ga:pagePath=~^/collections/human-genetics$' \
                   ',ga:pagePath=~^/interviews/working-lives$' \
                   ',ga:pagePath=~^/collections/natural-history-model-organisms$' \
                   ',ga:pagePath=~^/natural-history-of-model-organisms$' \
                   ',ga:pagePath=~^/collections/reproducibility-project-cancer-biology$' \
                   ',ga:pagePath=~^/collections/plain-language-summaries$' \
                   ',ga:pagePath=~^/interviews/early-career-researchers$'
        actual = ga3.generic_query_processor(models.COLLECTION, frame)
        self.assertEqual(actual, expected)


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
        results = ga3.parse_map_file(frame, contents)
        expected = OrderedDict([
            ('/new-study-1-in-4-sharks-and-rays-threatened-with-extinction-national-geographic', 'fbbb5b76'),
            ('/u-k-panel-backs-open-access-for-all-publicly-funded-research-papers', 'fbbcdd2b'),
            ('/elife-news/uk-panel-backs-open-access-all-publicly-funded-research-papers', 'fbbcdd2b')])
        self.assertEqual(results, expected)

def test_build_ga_query__invalid_dates_dropped():
    today = date(year=2015, month=6, day=1)
    invalid_cases = [
        # yesterday, invalid
        (date(year=2015, month=5, day=31), date(year=2015, month=5, day=31)),
        # today, invalid
        (date(year=2015, month=6, day=1), date(year=2015, month=6, day=1)),
        # tomorrow, invalid
        (date(year=2015, month=6, day=2), date(year=2015, month=6, day=2)),
    ]
    with patch('metrics.logic.date_today', return_value=today):
        for start_date, end_date in invalid_cases:
            frame = logic.build_ga_query(models.EVENT, start_date, end_date)
            assert frame == []

def test_build_ga_query__invalid_date_ranges_truncated():
    # start of year to today is truncated to day before yesterday
    today = date(year=2015, month=6, day=1)
    start_date = date(year=2015, month=1, day=1)
    invalid_cases = [
        # yesterday
        date(year=2015, month=5, day=31),
        # today
        date(year=2015, month=6, day=1),
        # tomorrow
        date(year=2015, month=6, day=2),
    ]
    expected_end_date = date(year=2015, month=5, day=30)
    with patch('metrics.logic.date_today', return_value=today):
        for end_date in invalid_cases:
            query_list = logic.build_ga_query(models.EVENT, start_date, end_date)
            assert len(query_list) == 1 # one interesting frame
            frame, query = query_list[0]
            assert query['end_date'] == expected_end_date
