import shutil
import pytest
from unittest import skip
import responses
from unittest.mock import patch, Mock
import requests
import os
import json
from os.path import join
from article_metrics import handler
import tempfile
from requests.exceptions import Timeout

@pytest.fixture(name='temp_dump_path')
def fixture_temp_dump_path(settings):
    name = tempfile.mkdtemp()
    settings.DUMP_PATH = name
    yield name
    shutil.rmtree(name)

def test_error_caught(temp_dump_path):
    "the handler logger records the exception (but doesn't swallow it)"
    with patch('article_metrics.handler.LOG') as log_mock:
        with pytest.raises(requests.exceptions.InvalidSchema):
            handler.requests_get('htp:/tly.wrong')
        assert 1 == log_mock.exception.call_count

def test_error_captured(temp_dump_path):
    "the handler writes a file on a bad request with details of the request and response"
    with patch('article_metrics.handler.LOG') as log_mock:
        opid = handler.opid()
        with pytest.raises(requests.exceptions.ConnectionError):
            handler.requests_get('http://asdfasdfasdf.elifesciences.org', opid=opid)

        # an exception is captured
        assert 1 == log_mock.exception.call_count

        # a file exists with the details
        expected_path = join(temp_dump_path, opid, 'log')
        assert os.path.isfile(expected_path)

        # at time of writing, a single line of json is written to a file for uncaught network errors
        log_contents = json.load(open(expected_path, 'r'))
        assert log_contents['id'] == opid

@responses.activate
def test_non2xx_response_written(temp_dump_path):
    "contents of error response is written to a file. contents of request is written"

    opid = handler.opid()
    bad_url = 'http://example.org'
    expected_body_content = 'pants'

    responses.add(responses.GET, bad_url, **{
        'body': expected_body_content,
        'status': 404,
        'content_type': 'text/plain'})

    # non 2xx response
    with pytest.raises(requests.exceptions.HTTPError):
        handler.requests_get(bad_url, opid=opid)

    # a file exists with the details
    expected_path = join(temp_dump_path, opid, 'log')
    assert os.path.isfile(expected_path)

    # a file exists with the body content
    expected_path = join(temp_dump_path, opid, 'body')
    assert os.path.isfile(expected_path)
    assert expected_body_content == open(expected_path, 'r').read()

@responses.activate
def test_custom_error_handler_404(temp_dump_path):
    opid = handler.opid()
    bad_url = 'http://example.org'
    expected_body_content = 'pants'

    responses.add(responses.GET, bad_url, **{
        'body': expected_body_content,
        'status': 499,
        'content_type': 'text/plain'})

    mk = Mock()
    handler.requests_get(bad_url, opid=opid, opts={499: mk})
    assert mk.called
    # 2019-03-11: pylint upgrade to 2.3.0 introduces this false positive
    # https://docs.python.org/3/library/unittest.mock.html#unittest.mock.Mock.call_args
    # pylint: disable=unsubscriptable-object
    resp_opid, resp_err = mk.call_args[0]
    assert resp_opid == opid
    assert resp_err.response.status_code == 499

@skip("can't replicate this scenario. responses mocks the retry functionality away and I can't/won't dig deep enough into python's urllib3 to find where the `max_retries` is handled")
@responses.activate
def test_network_connection_error_retry(temp_dump_path):
    "a connection is attempted three times before failing"
    kaboom = Timeout("tick tick tick BOOOOOOM")

    some_url = 'https://example.org'
    responses.add(responses.GET, some_url, **{
        'body': kaboom,
        'content_type': 'text/plain'})

    # we expect it to eventually die
    with pytest.raises(Timeout):
        handler.requests_get(some_url)

    # after dying three previous times
    assert len(responses.calls) == 3
