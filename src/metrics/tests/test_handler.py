from mock import patch
import requests
import os
import json
from os.path import join
from django.conf import settings
from metrics import handler, utils
from . import base

class One(base.BaseCase):
    def setUp(self):
        self.tempdir, self.rmdir = utils.tempdir()

    def tearDown(self):
        self.rmdir()

    @patch('metrics.handler.LOG')
    def test_error_caught(self, mock):
        "the handler logger records the exception (but doesn't swallow it)"
        self.assertRaises(requests.exceptions.InvalidSchema,
                          handler.requests_get, 'htp:/tly.wrong')
        mock.exception.assert_called_once()

    @patch('metrics.handler.LOG')
    def test_error_captured(self, mock):
        "the handler writes a file on a bad request with details of the request and response"
        opid = handler.opid()

        self.assertRaises(requests.exceptions.ConnectionError,
                          handler.requests_get, 'http://asdfasdfasdf.elifesciences.org', opid=opid)
        # an exception is captured
        mock.exception.assert_called_once()

        # a file exists with the details
        expected_path = join(settings.DUMP_PATH, opid, 'log')
        self.assertTrue(os.path.isfile(expected_path))

        # at time of writing, a single line of json is written to a file for uncaught network errors
        log_contents = json.load(open(expected_path, 'r'))
        self.assertEqual(log_contents['id'], opid)
