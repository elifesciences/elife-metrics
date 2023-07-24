from unittest import mock
from . import base
from datetime import datetime, timedelta
from article_metrics.ga_metrics import utils
from article_metrics.ga_metrics import core, elife_v1, elife_v2, elife_v3, elife_v4, elife_v5, elife_v6, elife_v7

class One(base.SimpleBaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_module_picker_daily(self):
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
        ]
        for dt, expected_module in expectations:
            self.assertEqual(expected_module, core.module_picker(dt, dt),
                             'failed to pick %r for date starting %s' % (expected_module, dt))

    def test_module_picker_monthly(self):
        jan, feb, march, april, may, june = utils.dt_month_range_gen(
            datetime(year=2016, month=1, day=1), datetime(year=2016, month=6, day=30))

        dec2015 = datetime(year=2015, month=12, day=1), datetime(year=2015, month=12, day=31)
        june2017 = datetime(year=2017, month=6, day=1), datetime(year=2017, month=6, day=30)
        feb2020 = datetime(year=2020, month=2, day=1), datetime(year=2020, month=2, day=28)
        mar2020 = datetime(year=2020, month=3, day=1), datetime(year=2021, month=11, day=30)
        dec2021 = datetime(year=2021, month=12, day=1), datetime(year=2023, month=3, day=31)
        apr2023 = datetime(year=2023, month=4, day=1), datetime(year=2023, month=3, day=31)

        expectations = [
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
        for dtpair, expected_module in expectations:
            actual = core.module_picker(*dtpair)
            msg = 'given: %s, expected: %s. got %s' % (dtpair, expected_module, actual)
            self.assertEqual(expected_module, actual, msg)

def test_valid_dt_pair():
    now = datetime(year=2015, month=6, day=1, hour=0, minute=0, second=0)
    yesterday = now - timedelta(days=1)
    two_days_ago = yesterday - timedelta(days=1)
    tomorrow = now + timedelta(days=1)
    valid_cases = [
        # months ago, valid
        (datetime(year=2015, month=1, day=1), datetime(year=2015, month=1, day=2)),
        # the day before yesterday, valid
        (two_days_ago, two_days_ago),
        # range ending the day before yesterday, valid
        (datetime(year=2015, month=1, day=1), two_days_ago),
    ]
    invalid_cases = [
        # today, invalid, partial results
        (now, now),
        # yesterday, invalid, partial results
        (yesterday, yesterday),
        # range involving today, invalid, partial results
        (yesterday, now),
        # range involving yesterday, invalid, partial results
        (two_days_ago, yesterday),
        # future date, invalid
        (tomorrow, tomorrow),
        # range involving a future date, invalid, partial results
        (two_days_ago, tomorrow),
    ]
    inception = datetime(year=2001, month=1, day=1)
    with mock.patch('article_metrics.ga_metrics.core.datetime_now', return_value=now):
        for case in valid_cases:
            assert core.valid_dt_pair(case, inception)
        for case in invalid_cases:
            assert not core.valid_dt_pair(case, inception)
