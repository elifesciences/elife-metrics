from metrics import utils
import base
import pytz
from datetime import datetime

class TestUtils(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_isint(self):
        int_list = [
            1,
            -1,
            '-1',
            '1',
            '1111111111',
            '99999999999999999999999999999999999',
            0xDEADBEEF, # hex
        ]
        for int_val in int_list:
            self.assertTrue(utils.isint(int_val))

    def test_isnotint(self):
        not_int_list = ['one', 'a', utils]
        for not_int in not_int_list:
            print('testing', not_int)
            self.assertFalse(utils.isint(not_int))

    def test_nth(self):
        expected_list = [
            ('abc', 0, 'a'),
            ('abc', 1, 'b'),
            ('abc', 2, 'c'),
            ('abc', 3, None),
            ('abc', -1, 'c'),
            ('abc', -3, 'a'),
            ('abc', -4, None),

            ([1, 2, 3], 0, 1),
            ([], 0, None),
            ((1, 2, 3), 0, 1),

            (None, 0, None),
            (None, -1, None),
            (None, 1, None),
        ]
        for val, idx, expected in expected_list:
            print('testing', val, idx, expected)
            self.assertEqual(utils.nth(idx, val), expected)

    def test_bad_nths(self):
        bad_list = [
            ({}, 0),
            ({'a': 1}, 0),
            #(None, 0), # attempting to access something in a None now gives you None
        ]
        for val, idx in bad_list:
            self.assertRaises(TypeError, utils.nth, idx, val)

    def test_first(self):
        expected_list = [
            (utils.first, [1, 2, 3], 1),
            (utils.first, (1, 2, 3), 1),
            (utils.first, 'abc', 'a'),
        ]
        for fn, val, expected in expected_list:
            self.assertEqual(fn(val), expected)

    def test_utcnow(self):
        "utcnow returns a UTC datetime"
        # TODO: this test could be improved
        now = utils.utcnow()
        self.assertEqual(now.tzinfo, pytz.utc)

    def test_todt(self):
        cases = [
            # naive dtstr becomes utc
            ("2001-01-01", \
             datetime(year=2001, month=1, day=1, tzinfo=pytz.utc)),

            # aware but non-utc become utc
            ("2001-01-01T23:30:30+09:30", \
             datetime(year=2001, month=1, day=1, hour=14, minute=0, second=30, tzinfo=pytz.utc)),
        ]
        for string, expected in cases:
            self.assertEqual(utils.todt(string), expected)

    def test_doi_to_msid(self):
        cases = [
            ('10.7554/eLife.09560', 9560),
            ('10.7554/eLife.09560.001', 9560),
        ]
        for given, expected in cases:
            self.assertEqual(utils.doi2msid(given), expected)

    def test_msid_to_doi(self):
        self.assertEqual(utils.msid2doi(3), '10.7554/eLife.00003')
        self.assertEqual(utils.msid2doi(10627), '10.7554/eLife.10627')
