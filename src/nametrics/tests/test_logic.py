from . import base
import os
from metrics import utils
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

class Two(base.BaseCase):
    def setUp(self):
        self.tmpdir, self.tmpdir_killer = utils.tempdir()

    def tearDown(self):
        self.tmpdir_killer()
        pass

    def test_build_ga_query(self):
        "the list of queries returned has the right shape"
        jan18 = date(year=2018, month=1, day=1)
        feb18 = date(year=2018, month=2, day=28)
        dec18 = date(year=2018, month=12, day=31)
        ql = logic.build_ga_query(models.EVENT, jan18, dec18)
        self.assertEqual(len(ql), 6) # 6 * 2 month chunks
        # the range is correct
        self.assertEqual(ql[0]['start_date'].date(), jan18)
        self.assertEqual(ql[-1]['end_date'].date(), dec18)
        # the first chunk is correct
        self.assertEqual(ql[0]['end_date'].date(), feb18)

    def test_build_ga_query_single(self):
        jan18 = date(year=2018, month=1, day=1)
        ql = logic.build_ga_query(models.EVENT, jan18, jan18) # two start dates...
        self.assertEqual(len(ql), 1)
        self.assertEqual(ql[0]['start_date'].date(), jan18)
        self.assertEqual(ql[0]['end_date'].date(), date(year=2018, month=1, day=31)) # end date maximised
        
    def test_load_ptype_history(self):
        logic.load_ptype_history(models.EVENT)

    def test_load_missing_ptype_history(self):
        self.assertRaises(ValueError, logic.load_ptype_history, "pants")

    def test_query_ga(self):
        "a standard response from GA is handled as expected, a dump file is created etc"
        jan18 = date(year=2018, month=1, day=1)
        q = logic.build_ga_query(models.EVENT, jan18, jan18)[0]
        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events.json'), 'r'))
        dumpfile = os.path.join(self.tmpdir, "pants.json")
        with patch('metrics.ga_metrics.core.output_path_from_results', return_value=dumpfile):
            with patch('metrics.ga_metrics.core.query_ga', return_value=fixture):
                result = logic.query_ga(models.EVENT, q)
                self.assertEqual(result, fixture) # nametrics.logic.query_ga is just a thin wrapper for now
                # ensure the dump file was written for debugging/loading later
                contents = os.listdir(self.tmpdir)
                self.assertEqual(len(contents), 1)
                self.assertEqual(json.load(open(dumpfile, 'r')), fixture)

    def test_process_response(self):
        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events.json'), 'r'))
        with patch('metrics.ga_metrics.core.output_path_from_results'):
            logic.process_response(models.EVENT, fixture)
            
