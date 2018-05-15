from . import base
from nametrics import models, views
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
        self.fail()
