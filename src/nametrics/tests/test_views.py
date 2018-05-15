from . import base
import os, json
from nametrics import models, views, logic
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
                for period in ['day', 'month']:
                    resp = self.c.get(url, {'period': period})
                    self.assertEqual(resp.status_code, 404)

    def test_request(self):
        # populate db
        fixture = json.load(open(os.path.join(self.fixture_dir, 'ga-response-events.json'), 'r'))
        frame = {'prefix': '/events'}
        rows = logic.aggregate(logic.process_response(models.EVENT, frame, fixture))
        logic.update_page_counts(models.EVENT, rows)

        models.Page.objects.get(identifier=models.LANDING_PAGE)

        # landing page
        url = reverse(views.metrics, kwargs={'ptype': models.EVENT})
        resp = self.c.get(url, {'period': logic.DAY})
        self.assertEqual(resp.status_code, 200)

        expected =  {
            'periods': [
              {'period': '2018-01-31', 'value': 1},
              {'period': '2018-01-30', 'value': 2},
              {'period': '2018-01-29', 'value': 1},
              {'period': '2018-01-26', 'value': 1},
              {'period': '2018-01-25', 'value': 3},
              {'period': '2018-01-24', 'value': 1},
              {'period': '2018-01-23', 'value': 3},
              {'period': '2018-01-18', 'value': 1},
              {'period': '2018-01-16', 'value': 4},
              {'period': '2018-01-15', 'value': 2},
              {'period': '2018-01-12', 'value': 1},
              {'period': '2018-01-11', 'value': 6},
              {'period': '2018-01-10', 'value': 2},
              {'period': '2018-01-09', 'value': 2},
              {'period': '2018-01-08', 'value': 1},
              {'period': '2018-01-05', 'value': 1},
              {'period': '2018-01-04', 'value': 2}],
            'totalPeriods': 17,
            'totalValue': 34}
        self.assertEqual(resp.json(), expected)
