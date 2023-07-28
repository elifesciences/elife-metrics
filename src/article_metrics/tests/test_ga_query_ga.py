import datetime
from unittest import mock
import pytest
from article_metrics.ga_metrics import core
from apiclient import errors

# because you can't do: setattr(object(), 'foo', 'bar')
class Object(object):
    pass

class DummyQuery(object):
    def __init__(self, raises):
        self.resp = Object()
        self.content = b'{"data": {"error": {"message": "dummy error message"}}}'
        attrs = {
            'reason': 'dummy reason',
            'status': raises,
            # 'data': {'error': {'message': None}},
        }
        [setattr(self.resp, key, val) for key, val in attrs.items()]

    def execute(self):
        raise errors.HttpError(self.resp, self.content)

def test_exponential_backoff_applied_on_rate_limit():
    query = DummyQuery(raises=503)
    with pytest.raises(AssertionError):
        core._query_ga(query, num_attempts=1)

def test_hard_fail_on_invalid_date():
    now = datetime.datetime(year=2015, month=6, day=1)
    cases = [
        # '2015-05-30', # two days ago, a-ok
        '2015-05-31', # one day ago, die
        '2015-06-01', # today, die
        '2015-06-02', # future date, die
    ]
    with mock.patch('article_metrics.ga_metrics.core.datetime_now', return_value=now):
        with pytest.raises(AssertionError):
            for case in cases:
                core.query_ga({'end_date': case})
