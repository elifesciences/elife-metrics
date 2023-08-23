import shutil
import json
import tempfile
import pytest
from os.path import join
from unittest import mock
from . import base
from datetime import datetime, timedelta
from article_metrics.utils import datetime_now
from article_metrics.ga_metrics import utils
from article_metrics.ga_metrics import core, elife_v1, elife_v2, elife_v3, elife_v4, elife_v5, elife_v6, elife_v7, elife_v8
from django.conf import settings
import apiclient

@pytest.fixture(name='test_output_dir')
def fixture_test_output_dir():
    name = tempfile.mkdtemp()
    yield name
    shutil.rmtree(name)

@pytest.fixture(name='temp_json_file')
def fixture_temp_json_file():
    with tempfile.NamedTemporaryFile() as temp_json_file:
        temp_json_file.write(b'''{"foo": "bar"}\n''')
        temp_json_file.seek(0)
        yield temp_json_file

def test_module_picker_daily():
    d1 = timedelta(days=1)
    expectations = [
        # on the big day, we still use v1 of the urls
        (core.SITE_SWITCH, elife_v1),
        # prior to the switchover, we used v1
        (core.SITE_SWITCH - d1, elife_v1),
        # after switchover, we now use v2
        (core.SITE_SWITCH + d1, elife_v2),

        # versionless urls
        # after switchover but before the versionless urls, we use v2
        (core.VERSIONLESS_URLS - d1, elife_v2),
        # on the day, we still use v2
        (core.VERSIONLESS_URLS, elife_v2),
        # on the day AFTER, we use v3
        (core.VERSIONLESS_URLS + d1, elife_v3),

        # on the day of the 2.0 switch, we use v4 urls
        (core.SITE_SWITCH_v2, elife_v4),

        # on the day of the addition of /executable, we use v5 urls
        (core.RDS_ADDITION, elife_v5),

        # on the day *after* the capturing of url parameters, we use v6 urls
        (core.URL_PARAMS + d1, elife_v6),

        # on the day of the GA4 switch, we use v7 urls
        (core.GA4_SWITCH, elife_v7),

        # on the day the Downloads died, we use file_downloads
        (core.GA4_DOWNLOADS_SWITCH, elife_v8),
    ]
    for dt, expected_module in expectations:
        assert expected_module == core.module_picker(dt, dt), \
            'failed to pick %r for date starting %s' % (expected_module, dt)

def test_module_picker_monthly():
    jan, feb, march, april, may, june = utils.dt_month_range_gen(
        datetime(year=2016, month=1, day=1), datetime(year=2016, month=6, day=30))

    dec2015 = datetime(year=2015, month=12, day=1), datetime(year=2015, month=12, day=31)
    june2017 = datetime(year=2017, month=6, day=1), datetime(year=2017, month=6, day=30)
    feb2020 = datetime(year=2020, month=2, day=1), datetime(year=2020, month=2, day=28)
    mar2020 = datetime(year=2020, month=3, day=1), datetime(year=2021, month=11, day=30)
    dec2021 = datetime(year=2021, month=12, day=1), datetime(year=2023, month=3, day=31)
    apr2023 = datetime(year=2023, month=4, day=1), datetime(year=2023, month=3, day=31)

    cases = [
        # on the day, we still use v1 of the urls
        (jan, elife_v1),
        # previous to the switchover, we used v1
        (dec2015, elife_v1),
        # after switchover, we use v2
        (feb, elife_v2),
        (march, elife_v2),

        # in the month versionless are introduced, use v3
        (may, elife_v3),
        # after versionless, we use v3
        (june, elife_v3),

        # on the month of the 2.0 switch, we use 2.0/v4 urls
        (june2017, elife_v4),

        # on the month of the addition of /executable , we continue using v4 urls
        (feb2020, elife_v4),

        # on the month after, we switch to v5
        (mar2020, elife_v5),

        (dec2021, elife_v6),

        (apr2023, elife_v7),
    ]
    for dtpair, expected_module in cases:
        actual = core.module_picker(*dtpair)
        msg = 'given: %s, expected: %s. got %s' % (dtpair, expected_module, actual)
        assert expected_module == actual, msg

def test_valid_dt_pair():
    now = datetime(year=2015, month=6, day=1, hour=0, minute=0, second=0)
    yesterday = now - timedelta(days=1)
    two_days_ago = yesterday - timedelta(days=1)
    tomorrow = now + timedelta(days=1)
    valid_cases = [
        # daily
        # some distant past date
        (datetime(year=2015, month=1, day=1), datetime(year=2015, month=1, day=2)),
        # the day before yesterday, valid, but potentially invalid results
        (two_days_ago, two_days_ago),
        # yesterday, valid, partial results
        (yesterday, yesterday),
        # today, valid, partial results
        (now, now),
        # daily, future date, empty results
        (tomorrow, tomorrow),

        # ranges
        # a range ending the day before yesterday, valid, potentially partial results.
        (datetime(year=2015, month=1, day=1), two_days_ago),
        # a range involving today, valid, partial results
        (yesterday, now),
        # a range involving yesterday, valid, potentially partial results
        (two_days_ago, yesterday),
        # a range involving a future date, valid, partial results
        (two_days_ago, tomorrow),
    ]
    inception = datetime(year=2001, month=1, day=1)
    with mock.patch('article_metrics.ga_metrics.core.datetime_now', return_value=now):
        for case in valid_cases:
            assert core.valid_dt_pair(case, inception), "expected valid: %s" % (case,)

def test_output_path_for_view_results(test_output_dir):
    "the output path is correctly generated for views"
    response = base.fixture_json('views-2016-02-24.json')
    expected = join(test_output_dir, settings.GA_OUTPUT_SUBDIR, "views/2016-02-24.json")
    path = core.output_path_from_results(response)
    assert expected == path

def test_output_path_for_download_results(test_output_dir):
    "the output path is correctly generated for downloads"
    response = base.fixture_json('views-2016-02-24.json')
    response['query']['filters'] = 'ga:eventLabel' # downloads are counted as events
    expected = join(test_output_dir, settings.GA_OUTPUT_SUBDIR, "downloads/2016-02-24.json")
    path = core.output_path_from_results(response)
    assert expected == path

def test_output_path_for_partial_daily_results():
    "partial, or potentially partial, daily results are not cached."
    today = datetime_now().strftime('%Y-%m-%d')
    response = base.fixture_json('views-2016-02-24.json')
    response['query']['start-date'] = today
    response['query']['end-date'] = today
    # lsh@2023-07-25: disabled cache paths for potentially partial/empty results.
    #expected = join(test_output_dir, settings.GA_OUTPUT_SUBDIR, "views/%s.json" % today)
    expected = None
    path = core.output_path_from_results(response)
    assert expected == path

def test_output_path_for_partial_monthly_results():
    "partial monthly results are not cached"
    today = datetime(year=2001, month=1, day=15)
    response = base.fixture_json('views-2016-02-24.json')
    response['query']['start-date'] = "2001-01-01"
    response['query']['end-date'] = "2001-01-31"
    expected = None
    with mock.patch('article_metrics.ga_metrics.core.datetime_now', return_value=today):
        path = core.output_path_from_results(response)
        assert expected == path

def test_output_path_for_unknown_results():
    "a helpful assertion error is raised if we're given results that can't be parsed"
    with pytest.raises(AssertionError):
        core.output_path_from_results({})

def test_ga_response_sanitised():
    "responses from GA have certain values scrubbed from them"
    raw_response = base.fixture_json('views-2016-02-24.json.raw')
    response = core.sanitize_ga_response(raw_response)
    for key in core.SANITISE_THESE:
        assert key not in response

def test_ga_response_sanitised_when_written(test_output_dir):
    "responses from GA have certain values scrubbed from them before being written to disk"
    raw_response = base.fixture_json('views-2016-02-24.json.raw')
    output_path = join(test_output_dir, 'foo.json')
    core.write_results(raw_response, output_path)
    response = json.load(open(output_path, 'r'))
    for key in core.SANITISE_THESE:
        assert key not in response

# ---

# because you can't do: setattr(object(), 'foo', 'bar')
class Object(object):
    pass

class DummyQuery(object):
    def __init__(self, raises):
        self.resp = Object()
        self.resp.reason = 'dummy reason'
        self.resp.status = raises
        self.content = b'{"data": {"error": {"message": "dummy error message"}}}'

    def execute(self):
        raise apiclient.errors.HttpError(self.resp, self.content)

def test_exponential_backoff_applied_on_rate_limit():
    query = DummyQuery(raises=503)
    with pytest.raises(AssertionError):
        core._query_ga(query, num_attempts=1)

# ---

def test_load_cache(temp_json_file):
    past_dt = datetime(year=2001, month=1, day=1)
    future_dt = datetime(year=2050, month=1, day=1)
    uncacheable_dt1 = datetime_now()
    uncacheable_dt2 = datetime_now() - timedelta(days=1)
    uncacheable_dt3 = datetime_now() - timedelta(days=2)
    cacheable_dt = datetime_now() - timedelta(days=4)

    cached_data = {'foo': 'bar'}
    no_data = None

    cases = [
        # cached data available and only cached is true, return cached data
        (('views', past_dt, past_dt, True, True), cached_data),
        # cached data available but only cached is false, return cached data
        (('views', past_dt, past_dt, True, False), cached_data),

        # recent cacheable data available
        (('views', cacheable_dt, cacheable_dt, True, False), cached_data),

        # recent cacheable data unavailable
        (('views', uncacheable_dt1, uncacheable_dt1, True, False), no_data),
        (('views', uncacheable_dt2, uncacheable_dt2, True, False), no_data),
        (('views', uncacheable_dt3, uncacheable_dt3, True, False), no_data),

        # uncacheable data, bad date
        (('views', future_dt, future_dt, True, False), no_data),
    ]

    with mock.patch('article_metrics.ga_metrics.core.output_path_v2', return_value=temp_json_file.name):
        for (results_type, start_dt, end_dt, cached, only_cached), expected in cases:
            actual = core.load_cache(results_type, start_dt, end_dt, cached, only_cached)
            assert actual == expected

    # valid date, use cached, use only cached, but no cached data available
    with mock.patch('article_metrics.ga_metrics.core.output_path_v2', return_value='/path/does/not/exist'):
        expected = {}
        actual = core.load_cache(results_type, cacheable_dt, cacheable_dt, True, True)
        assert actual == expected
