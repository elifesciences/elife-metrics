from . import base
from unittest.mock import patch
from metrics.crossref import citations as crossref
from metrics import utils
import responses

class One(base.BaseCase):
    def setUp(self):
        self.tempdir, self.rmdir = utils.tempdir()

    def tearDown(self):
        self.rmdir()

    @responses.activate
    @patch('metrics.handler.LOG')
    def test_fetch_401_response(self, mock):
        "not authorised"

        responses.add(responses.GET, crossref.URL, **{
            'body': 'uwotmt?',
            'status': 401,
            'content_type': 'text/plain'})

        bad_doi = '10.7554/eLife.02740.027'

        with self.settings(DUMP_PATH=self.tempdir):
            expected_response = None
            self.assertEqual(expected_response, crossref.fetch(bad_doi))
            self.assertTrue(mock.warn.called) # logged
