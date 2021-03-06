from . import base
import os, json
from metrics import models, views, logic, history
from article_metrics import utils
from django.urls import reverse
from django.test import Client

class One(base.BaseCase):
    def setUp(self):
        self.c = Client()

    def tearDown(self):
        pass

    def test_request_empty_db(self):
        "regular requests fail with a 404 when the database is empty"
        dummy_pid_list = ['foo', 'bar', 'baz', 1, 2, 3]
        for pid in dummy_pid_list:
            for ptype in models.PAGE_TYPES: # press-packages, etc
                url = reverse(views.metrics, kwargs={'ptype': ptype, 'pid': pid})
                for period in [logic.DAY, logic.MONTH]:
                    resp = self.c.get(url, {'by': period})
                    self.assertEqual(resp.status_code, 404)

class Two(base.BaseCase):
    def setUp(self):
        # populate db
        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events-frame2.json'), 'r'))
        frame = {'id': '2', 'prefix': '/events'}
        rows = logic.aggregate(logic.process_response(models.EVENT, frame, fixture))
        logic.update_page_counts(models.EVENT, rows)
        self.c = Client()

    def test_request_day_periods(self):
        url = reverse(views.metrics, kwargs={'ptype': models.EVENT})
        resp = self.c.get(url, {'by': logic.DAY})
        self.assertEqual(resp.status_code, 200)

        expected = {
            'periods': [
                {'period': '2018-01-31', 'value': 2},
                {'period': '2018-01-30', 'value': 5},
                {'period': '2018-01-29', 'value': 9},
                {'period': '2018-01-26', 'value': 1},
                {'period': '2018-01-25', 'value': 5},
                {'period': '2018-01-24', 'value': 6},
                {'period': '2018-01-23', 'value': 4},
                {'period': '2018-01-22', 'value': 1},
                {'period': '2018-01-19', 'value': 3},
                {'period': '2018-01-18', 'value': 1},
                {'period': '2018-01-17', 'value': 2},
                {'period': '2018-01-16', 'value': 7},
                {'period': '2018-01-15', 'value': 3},
                {'period': '2018-01-12', 'value': 2},
                {'period': '2018-01-11', 'value': 10},
                {'period': '2018-01-10', 'value': 3},
                {'period': '2018-01-09', 'value': 3},
                {'period': '2018-01-08', 'value': 2},
                {'period': '2018-01-05', 'value': 1},
                {'period': '2018-01-04', 'value': 5}],
            'totalPeriods': 22,
            'totalValue': 79}

        self.assertEqual(resp.json(), expected)

    def test_request_month_periods(self):
        url = reverse(views.metrics, kwargs={'ptype': models.EVENT})
        resp = self.c.get(url, {'by': logic.MONTH})
        self.assertEqual(resp.status_code, 200)
        expected = {
            'periods': [
                {'period': '2018-01', 'value': 79},
            ],
            'totalPeriods': 1,
            'totalValue': 79
        }
        self.assertEqual(resp.json(), expected)

class Three(base.BaseCase):
    def setUp(self):
        self.c = Client()
        self.spec_content_types = history.load_from_file().keys()
        # create a page "asdf" for every content type in history file
        # this itself may fail if models.PAGE_TYPES hasn't been updated
        self.dummy_id = "asdf"
        for sct in self.spec_content_types:
            ptype, _, _ = utils.create_or_update(models.PageType, {"name": sct}, update=False)
            utils.create_or_update(models.Page, {"type": ptype, "identifier": self.dummy_id})

    def test_content_types(self):
        "ensure all content types in history schema"
        expected_result = {'periods': [], 'totalPeriods': 0, 'totalValue': 0}
        for sct in self.spec_content_types:
            resp = self.c.get(reverse(views.metrics, kwargs={'ptype': sct, 'pid': self.dummy_id}))
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), expected_result)
