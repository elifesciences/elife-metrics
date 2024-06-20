import typing
from article_metrics import utils, models
import pytz
from datetime import datetime, date
from django.conf import settings
import pytest
import requests
from unittest.mock import Mock

@pytest.mark.django_db
def test_create_or_update():
    obj, created, updated = utils.create_or_update(models.Article, {'doi': '10.7554/eLife.1234'})
    assert obj
    assert created is True
    assert updated is False

@pytest.mark.django_db
def test_create_or_update_bad_keylist():
    utils.create_or_update(models.Article, {'doi': '10.7554/eLife.1234', 'pmid': 1})
    with pytest.raises(AssertionError):
        utils.create_or_update(models.Article, {'pmid': 1}, key_list=['???'])

def test_isint():
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
        assert utils.isint(int_val)

def test_isnotint():
    not_int_list = ['one', 'a', utils]
    for not_int in not_int_list:
        assert not utils.isint(not_int), "failed on %s" % not_int

def test_nth():
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
        assert utils.nth(idx, val) == expected, "failed: %s %s %s" % (val, idx, expected)

def test_bad_nths():
    bad_list = [
        ({}, 0),
        ({'a': 1}, 0),
        # (None, 0), # attempting to access something in a None now gives you None
    ]
    for val, idx in bad_list:
        with pytest.raises(TypeError):
            utils.nth(idx, val)

def test_first():
    expected_list = [
        (utils.first, [1, 2, 3], 1),
        (utils.first, (1, 2, 3), 1),
        (utils.first, 'abc', 'a'),
    ]
    for fn, val, expected in expected_list:
        assert fn(val) == expected

def test_utcnow():
    "utcnow returns a UTC datetime"
    now = utils.utcnow()
    assert now.tzinfo == pytz.utc

def test_todt():
    cases = [
        # naive dtstr becomes utc
        ("2001-01-01", \
         datetime(year=2001, month=1, day=1, tzinfo=pytz.utc)),

        # aware but non-utc become utc
        ("2001-01-01T23:30:30+09:30", \
         datetime(year=2001, month=1, day=1, hour=14, minute=0, second=30, tzinfo=pytz.utc)),
    ]
    for string, expected in cases:
        assert utils.todt(string) == expected

def test_tod():
    cases = [
        # empties
        (None, None),
        ("", None),
        # string date
        ("2001-01-01", date(year=2001, month=1, day=1)),
        # string datetime, no tz
        ("2001-01-01T00:00:00", date(year=2001, month=1, day=1)),
        # string datetime, with tz
        ("2001-01-01T00:00:00Z", date(year=2001, month=1, day=1)),
        # string datetime, with tz in 'past'
        ("2001-01-01T00:00:00Z-23", date(year=2000, month=12, day=31)),
        # date
        (date(year=2001, month=1, day=1), date(year=2001, month=1, day=1)),
        # datetime, no tz
        (datetime(year=2001, month=1, day=1), date(year=2001, month=1, day=1)),
        # datetime, with tz
        (datetime(year=2001, month=1, day=1, tzinfo=pytz.utc), date(year=2001, month=1, day=1)),
    ]
    for given, expected in cases:
        assert utils.tod(given) == expected

def test_doi_to_msid():
    cases = [
        ('10.7554/eLife.09560', 9560),
        ('10.7554/eLife.09560.001', 9560),
        ('10.7554/elife.09560', 9560), # lowercase 'l' in 'elife'
    ]
    for given, expected in cases:
        assert utils.doi2msid(given) == expected

def test_bad_doi_to_msid():
    cases = [
        '',
        '10.7554/eLife.',
        '10.7554/eLife.0',
        '10.7554/eLife.0000000000000000000',

        '10.7555/eLife.09560', # bad prefix

            [], {}, 1, # non-strings
    ]
    for badegg in cases:
        with pytest.raises(AssertionError):
            utils.doi2msid(badegg)

def test_msid_to_doi():
    cases = [
        (3, '10.7554/eLife.00003'),
        (10627, '10.7554/eLife.10627')
    ]
    for given, expected in cases:
        assert utils.msid2doi(given) == expected

def test_paginate():
    cases = [
        ([1, 2, 3], 1, [[1], [2], [3]]),
        ([1, 2, 3], 2, [[1, 2], [3]]),
        ([1, 2, 3], 3, [[1, 2, 3]]),
        ([1, 2, 3], 4, [[1, 2, 3]]),
    ]
    for seq, rowlen, expected in cases:
        result = utils.paginate(seq, rowlen)
        assert isinstance(result, typing.Generator)
        assert list(result) == expected

def test_paginate_v2():
    cases = [
        ([1, 2, 3], 1, [[1], [2], [3]]),
        ([1, 2, 3], 2, [[1, 2], [3]]),
        ([1, 2, 3], 3, [[1, 2, 3]]),
        ([1, 2, 3], 4, [[1, 2, 3]]),
    ]
    # v2 handles regular lists like v1
    for seq, rowlen, expected in cases:
        result = utils.paginate_v2(seq, rowlen)
        assert isinstance(result, typing.Generator)
        assert list(result) == expected, 'failed case: %s' % expected

    # v2 also handles lazy lists
    for seq, rowlen, expected in cases:
        lazy_seq = iter(seq)
        result = utils.paginate_v2(lazy_seq, rowlen)
        assert isinstance(result, typing.Generator)
        assert list(result) == expected, 'failed case: %s' % expected

def test_flatten():
    cases = [
        ([], []),
        ([[1, 2, 3]], [1, 2, 3]),
        ([[1], [2], [3]], [1, 2, 3]),

        # lazy sequences
        (iter([[1, 2, 3]]), [1, 2, 3]),
        (iter([[1], [2], [3]]), [1, 2, 3]),
    ]
    for given, expected in cases:
        assert utils.flatten(given) == expected

def test_get_article_versions():
    article_id = '85111'

    requests.get = Mock()
    mock_response = Mock()
    mock_response.json.return_value = {'doiVersion': f'10.7554/eLife.{article_id}.3'}
    mock_response.raise_for_status.return_value = None
    requests.get.return_value = mock_response

    versions = utils.get_article_versions(article_id)

    assert versions == [1, 2, 3]
    requests.get.assert_called_once_with(f"{settings.LAX_URL}/{article_id}")

def test_get_article_versions_error():
    article_id = '85111'
    requests.get = Mock(side_effect=requests.exceptions.RequestException)

    versions = utils.get_article_versions(article_id)

    assert versions == []
    requests.get.assert_called_once_with(f"{settings.LAX_URL}/{article_id}")
