from unittest import skip
import responses
from mock import patch
import requests
import os
import json
from os.path import join
from django.conf import settings
from metrics import handler, utils
from . import base

from requests.exceptions import Timeout

class One(base.BaseCase):
    def setUp(self):
        self.tempdir, self.rmdir = utils.tempdir()

    def tearDown(self):
        self.rmdir()

    @patch('metrics.handler.LOG')
    def test_error_caught(self, mock):
        "the handler logger records the exception (but doesn't swallow it)"
        with self.settings(DUMP_PATH=self.tempdir):
            self.assertRaises(requests.exceptions.InvalidSchema,
                              handler.requests_get, 'htp:/tly.wrong')
            mock.exception.assert_called_once()

    @patch('metrics.handler.LOG')
    def test_error_captured(self, mock):
        "the handler writes a file on a bad request with details of the request and response"
        with self.settings(DUMP_PATH=self.tempdir):
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

    @responses.activate
    def test_non2xx_response_written(self):
        "contents of error response is written to a file. contents of request is written"

        opid = handler.opid()
        bad_url = 'http://elifesciences.org'
        expected_body_content = 'pants'

        responses.add(responses.GET, bad_url, **{
            'body': expected_body_content,
            'status': 404,
            'content_type': 'text/plain'})

        with self.settings(DUMP_PATH=self.tempdir):
            # non 2xx response
            self.assertRaises(requests.exceptions.HTTPError, handler.requests_get, bad_url, opid=opid)

            # a file exists with the details
            expected_path = join(settings.DUMP_PATH, opid, 'log')
            self.assertTrue(os.path.isfile(expected_path))

            # a file exists with the body content
            expected_path = join(settings.DUMP_PATH, opid, 'body')
            self.assertTrue(os.path.isfile(expected_path))
            self.assertEqual(open(expected_path, 'r').read(), expected_body_content)

    @skip("can't replicate this scenario. responses mocks the retry functionality away and I can't/won't dig deep enough into python's urllib3 to find where the `max_retries` is handled")
    @responses.activate
    def test_network_connection_error_retry(self):
        "a connection is attempted three times before failing"
        kaboom = Timeout("tick tick tick BOOOOOOM")

        some_url = 'https://example.org'
        responses.add(responses.GET, some_url, **{
            'body': kaboom,
            'content_type': 'text/plain'})

        # we expect it to eventually die
        self.assertRaises(Timeout, handler.requests_get, some_url)
        
        # after dying three previous times
        print responses.calls.__dict__
        self.assertEqual(len(responses.calls), 3)
