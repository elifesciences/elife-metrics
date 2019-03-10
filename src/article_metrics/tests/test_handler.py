from unittest import skip
import responses
from unittest.mock import patch, Mock
import requests
import os
import json
from os.path import join
from django.conf import settings
from article_metrics import handler, utils
from . import base

from requests.exceptions import Timeout

class One(base.BaseCase):
    def setUp(self):
        self.tempdir, self.rmdir = utils.tempdir()

    def tearDown(self):
        self.rmdir()

    @patch('article_metrics.handler.LOG')
    def test_error_caught(self, mock):
        "the handler logger records the exception (but doesn't swallow it)"
        with self.settings(DUMP_PATH=self.tempdir):
            self.assertRaises(requests.exceptions.InvalidSchema,
                              handler.requests_get, 'htp:/tly.wrong')
            # http://engineroom.trackmaven.com/blog/mocking-mistakes/
            # mock.exception.assert_called_once()
            self.assertEqual(1, mock.exception.call_count)

    @patch('article_metrics.handler.LOG')
    def test_error_captured(self, mock):
        "the handler writes a file on a bad request with details of the request and response"
        with self.settings(DUMP_PATH=self.tempdir):
            opid = handler.opid()
            self.assertRaises(requests.exceptions.ConnectionError,
                              handler.requests_get, 'http://asdfasdfasdf.elifesciences.org', opid=opid)

            # an exception is captured
            self.assertEqual(1, mock.exception.call_count)

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
        bad_url = 'http://example.org'
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

    @responses.activate
    def test_custom_error_handler_404(self):
        opid = handler.opid()
        bad_url = 'http://example.org'
        expected_body_content = 'pants'

        responses.add(responses.GET, bad_url, **{
            'body': expected_body_content,
            'status': 499,
            'content_type': 'text/plain'})

        with self.settings(DUMP_PATH=self.tempdir):
            mk = Mock()
            handler.requests_get(bad_url, opid=opid, opts={499: mk})
            self.assertTrue(mk.called)
            # 2019-03-11: pylint upgrade to 2.3.0 introduces this false positive
            # https://docs.python.org/3/library/unittest.mock.html#unittest.mock.Mock.call_args
            # pylint: disable=unsubscriptable-object
            resp_opid, resp_err = mk.call_args[0]
            self.assertEqual(resp_opid, opid)
            self.assertEqual(resp_err.response.status_code, 499)

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
        self.assertEqual(len(responses.calls), 3)
