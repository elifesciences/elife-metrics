import pytest
import shutil
import tempfile
from unittest.mock import patch
from article_metrics.crossref import citations as crossref
import responses

@pytest.fixture(name='temp_dump_path')
def fixture_temp_dump_path(settings):
    name = tempfile.mkdtemp()
    settings.DUMP_PATH = name
    yield name
    shutil.rmtree(name)

@responses.activate
def test_fetch_401_response(temp_dump_path):
    "not authorised"
    with patch('article_metrics.handler.LOG') as log_mock:
        responses.add(responses.GET, crossref.URL, **{
            'body': '???',
            'status': 401,
            'content_type': 'text/plain'})

        bad_doi = '10.7554/eLife.02740.027'

        expected_response = None
        assert expected_response == crossref.fetch(bad_doi)
        assert log_mock.warning.called
