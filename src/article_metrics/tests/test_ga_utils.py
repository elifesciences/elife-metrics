import os, json
from os.path import join
from . import base
from datetime import datetime
from article_metrics.ga_metrics import core, utils
from django.conf import settings

class TestUtils(base.SimpleBaseCase):
    def setUp(self):
        # TODO: switch to builtin temp dir
        self.test_output_dir = '/tmp/elife-ga-metrics/'
        os.system('mkdir ' + self.test_output_dir)
        os.environ['TESTING'] = "1"
        os.environ['TEST_OUTPUT_DIR'] = self.test_output_dir

    def tearDown(self):
        os.system('rm -rf ' + self.test_output_dir)
        pass

    def test_norm_table_id(self):
        cases = [
            ('12345678', 'ga:12345678'),
            (12345678, 'ga:12345678'),
            ('ga:12345678', 'ga:12345678'),
        ]
        for given, expected in cases:
            self.assertEqual(expected, utils.norm_table_id(given))

    def test_ymd(self):
        dt = datetime(year=1997, month=8, day=29, hour=6, minute=14) # UTC ;)
        self.assertEqual(core.ymd(dt), "1997-08-29")

    def test_enplumpen(self):
        self.assertEqual("10.7554/eLife.01234", utils.enplumpen("e01234"))

    def test_deplumpen(self):
        actual = utils.deplumpen("eLife.01234")
        self.assertEqual("e01234", actual)

    def test_deplumpen_failures(self):
        soft_cases = [
            ('asdf', 'asdf'),
            ('012345', '012345'),
        ]
        for given, expected in soft_cases:
            self.assertEqual(utils.deplumpen(given), expected)

        hard_cases = [None, [], {}, ()]
        for case in hard_cases:
            self.assertRaises(ValueError, utils.deplumpen, case)

    def test_month_min_max(self):
        cases = [
            ((2016, 1, 5), (2016, 1, 1), (2016, 1, 31)),
            ((2016, 2, 14), (2016, 2, 1), (2016, 2, 29)),
            ((2016, 3, 19), (2016, 3, 1), (2016, 3, 31)),
            ((2016, 4, 7), (2016, 4, 1), (2016, 4, 30)),
            ((2016, 5, 4), (2016, 5, 1), (2016, 5, 31)),
        ]
        for given_ymd, start_ymd, end_ymd in cases:
            actual_min_max = utils.month_min_max(datetime(*given_ymd))
            expected_min = datetime(*start_ymd)
            expected_max = datetime(*end_ymd)
            self.assertEqual(actual_min_max, (expected_min, expected_max))

    def test_month_range(self):
        expected_output = [
            (datetime(year=2014, month=12, day=1), datetime(year=2014, month=12, day=31)),
            (datetime(year=2015, month=1, day=1), datetime(year=2015, month=1, day=31)),
            (datetime(year=2015, month=2, day=1), datetime(year=2015, month=2, day=28)),
            (datetime(year=2015, month=3, day=1), datetime(year=2015, month=3, day=31)),
        ]
        start_dt = datetime(year=2014, month=12, day=15)
        end_dt = datetime(year=2015, month=3, day=12)
        self.assertEqual(expected_output, list(utils.dt_month_range(start_dt, end_dt)))

    def test_month_range_single_month(self):
        "when the given range falls within the same year+month"
        start_dt = end_dt = datetime(year=2014, month=12, day=15)
        expected_output = [
            (datetime(year=2014, month=12, day=1), datetime(year=2014, month=12, day=31)),
        ]
        self.assertEqual(list(utils.dt_month_range(start_dt, end_dt)), expected_output)

    def test_month_range_single_month_preserve_caps(self):
        "when the given range falls within the same year+month and the capping dates must be preserved"
        start_dt = end_dt = datetime(year=2014, month=12, day=15)
        expected_output = [
            (datetime(year=2014, month=12, day=15), datetime(year=2014, month=12, day=15)),
        ]
        self.assertEqual(list(utils.dt_month_range(start_dt, end_dt, preserve_caps=True)), expected_output)

    # output path

    def test_output_path_for_view_results(self):
        "the output path is correctly generated for views"
        response = json.load(open(join(self.fixture_dir, 'views-2016-02-24.json'), 'r'))
        expected_path = join(self.test_output_dir, settings.GA_OUTPUT_SUBDIR, "views/2016-02-24.json")
        path = core.output_path_from_results(response)
        self.assertEqual(path, expected_path)

    def test_output_path_for_download_results(self):
        "the output path is correctly generated for downloads"
        response = json.load(open(join(self.fixture_dir, 'views-2016-02-24.json'), 'r'))
        response['query']['filters'] = 'ga:eventLabel' # downloads are counted as events
        expected_path = join(self.test_output_dir, settings.GA_OUTPUT_SUBDIR, "downloads/2016-02-24.json")
        path = core.output_path_from_results(response)
        self.assertEqual(path, expected_path)

    def test_output_path_for_partial_results(self):
        "the output path is correctly generated for requests that generate partial responses"
        today = datetime.now().strftime('%Y-%m-%d')
        response = json.load(open(join(self.fixture_dir, 'views-2016-02-24.json'), 'r'))
        response['query']['start-date'] = today
        response['query']['end-date'] = today
        expected_path = join(self.test_output_dir, settings.GA_OUTPUT_SUBDIR, "views/%s.json.partial" % today)
        path = core.output_path_from_results(response)
        self.assertEqual(path, expected_path)

    def test_output_path_for_unknown_results(self):
        "a helpful assertion error is raised if we're given results that can't be parsed"
        self.assertRaises(AssertionError, core.output_path_from_results, {})

    # sanitise GA response

    def test_ga_response_sanitised(self):
        "responses from GA have certain values scrubbed from them"
        raw_response = json.load(open(join(self.fixture_dir, 'views-2016-02-24.json.raw'), 'r'))
        response = core.sanitize_ga_response(raw_response)
        for key in core.SANITISE_THESE:
            self.assertTrue(key not in response)

    def test_ga_response_sanitised_when_written(self):
        "responses from GA have certain values scrubbed from them before being written to disk"
        raw_response = json.load(open(join(self.fixture_dir, 'views-2016-02-24.json.raw'), 'r'))
        output_path = core.write_results(raw_response, join(self.test_output_dir, 'foo.json'))
        response = json.load(open(output_path, 'r'))
        for key in core.SANITISE_THESE:
            self.assertTrue(key not in response)
