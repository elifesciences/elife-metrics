import base
from metrics.ga_metrics import core
from apiclient import errors

import logging

LOG = logging.getLogger("")
LOG.level = logging.DEBUG

class Object(object):
    pass

class DummyQuery(object):
    def __init__(self, raises):
        self.resp = Object()
        self.content = '{"data": {"error": {"message": "dummy error message"}}}'
        attrs = {
            'reason': 'dummy reason',
            'status': raises,
            #'data': {'error': {'message': None}},
        }
        [setattr(self.resp, key, val) for key, val in attrs.items()]

    def execute(self):
        raise errors.HttpError(self.resp, self.content)

class TestQueryGA(base.SimpleBaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_exponential_backoff_applied_on_rate_limit(self):
        query = DummyQuery(raises=503)
        self.assertRaises(AssertionError, core.query_ga, query, num_attempts=1)
