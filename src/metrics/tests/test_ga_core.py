from . import base
from datetime import datetime, timedelta
from metrics.ga_metrics import utils
from metrics.ga_metrics import core, elife_v1, elife_v2, elife_v3, elife_v4

class One(base.SimpleBaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_module_picker_daily(self):
        d1 = timedelta(days=1)
        expectations = [
            # on the day, we still use v1 of the urls
            (core.SITE_SWITCH, elife_v1),
            # previous to the switchover, we used v1
            (core.SITE_SWITCH - d1, elife_v1),
            # after switchover, we use v2
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
        ]
        for dt, expected_module in expectations:
            self.assertEqual(expected_module, core.module_picker(dt, dt),
                             'failed to pick %r for date starting %s' % (expected_module, dt))

    def test_module_picker_monthly(self):
        jan, feb, march, april, may, june = utils.dt_month_range_gen(
            datetime(year=2016, month=1, day=1), datetime(year=2016, month=6, day=30))

        june2017 = datetime(year=2017, month=6, day=1), datetime(year=2017, month=6, day=30)

        expectations = [
            # on the day, we still use v1 of the urls
            (jan, elife_v1),
            # previous to the switchover, we used v1
            (feb, elife_v2),
            # after switchover, we use v2
            (march, elife_v2),

            # in the month versionless are introduced, use v3
            (may, elife_v3),
            # after versionless, we use v3
            (june, elife_v3),

            # on the month of the 2.0 switch, we use 2.0 urls
            (june2017, elife_v4)
        ]
        for dtpair, expected_module in expectations:
            actual = core.module_picker(*dtpair)
            msg = 'given: %s, expected: %s. got %s' % (dtpair, expected_module, actual)
            self.assertEqual(expected_module, actual, msg)
