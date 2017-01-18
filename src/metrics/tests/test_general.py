from base import BaseCase
from metrics.elife_ga_metrics import general, utils
from datetime import datetime
from collections import OrderedDict

class GeneralTests(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_monthly_average(self):
        sept_2015 = datetime(year=2015, month=9, day=1)
        dtrange = utils.dt_month_range(sept_2015, sept_2015)
        from_date, to_date = dtrange[0]

        resp = general.total_traffic_monthly(self.table_id, from_date, to_date)
        expected_resp = {'from_date': u'2015-09-01',
                         'to_date': u'2015-09-30',
                         'results': OrderedDict([(u'2015-09', 675857)]),
                         'average': 675857}
        self.assertEqual(resp, expected_resp)
