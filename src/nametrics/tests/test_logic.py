from . import base
from nametrics import logic

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

class Two(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_ga_ingest(self):
        pass
