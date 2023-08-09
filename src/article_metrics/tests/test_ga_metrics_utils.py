from datetime import datetime
from article_metrics.ga_metrics import utils
import pytest

def test_norm_table_id():
    cases = [
        ('12345678', 'ga:12345678'),
        (12345678, 'ga:12345678'),
        ('ga:12345678', 'ga:12345678'),
    ]
    for given, expected in cases:
        assert expected == utils.norm_table_id(given)

def test_ymd():
    dt = datetime(year=1997, month=8, day=29, hour=6, minute=14) # UTC ;)
    expected = "1997-08-29"
    assert expected == utils.ymd(dt)

def test_enplumpen():
    expected = "10.7554/eLife.01234"
    assert expected == utils.enplumpen("e01234")

def test_deplumpen():
    expected = "e01234"
    actual = utils.deplumpen("eLife.01234")
    assert expected == actual

def test_deplumpen_failures():
    soft_cases = [
        ('asdf', 'asdf'),
        ('012345', '012345'),
    ]
    for given, expected in soft_cases:
        assert expected == utils.deplumpen(given)

    hard_cases = [None, [], {}, ()]
    for case in hard_cases:
        with pytest.raises(ValueError):
            utils.deplumpen(case)

def test_month_min_max():
    cases = [
        ((2016, 1, 5), (2016, 1, 1), (2016, 1, 31)),
        ((2016, 2, 14), (2016, 2, 1), (2016, 2, 29)),
        ((2016, 3, 19), (2016, 3, 1), (2016, 3, 31)),
        ((2016, 4, 7), (2016, 4, 1), (2016, 4, 30)),
        ((2016, 5, 4), (2016, 5, 1), (2016, 5, 31)),
    ]
    for given_ymd, start_ymd, end_ymd in cases:
        expected = (datetime(*start_ymd), datetime(*end_ymd))
        actual = utils.month_min_max(datetime(*given_ymd))
        assert expected == actual

def test_month_range():
    expected_output = [
        (datetime(year=2014, month=12, day=1), datetime(year=2014, month=12, day=31)),
        (datetime(year=2015, month=1, day=1), datetime(year=2015, month=1, day=31)),
        (datetime(year=2015, month=2, day=1), datetime(year=2015, month=2, day=28)),
        (datetime(year=2015, month=3, day=1), datetime(year=2015, month=3, day=31)),
    ]
    start_dt = datetime(year=2014, month=12, day=15)
    end_dt = datetime(year=2015, month=3, day=12)
    assert expected_output == list(utils.dt_month_range(start_dt, end_dt))

def test_month_range_single_month():
    "when the given range falls within the same year+month"
    start_dt = end_dt = datetime(year=2014, month=12, day=15)
    expected_output = [
        (datetime(year=2014, month=12, day=1), datetime(year=2014, month=12, day=31)),
    ]
    assert expected_output == list(utils.dt_month_range(start_dt, end_dt))

def test_month_range_single_month_preserve_caps():
    "when the given range falls within the same year+month and the capping dates must be preserved"
    start_dt = end_dt = datetime(year=2014, month=12, day=15)
    expected_output = [
        (datetime(year=2014, month=12, day=15), datetime(year=2014, month=12, day=15)),
    ]
    assert expected_output == list(utils.dt_month_range(start_dt, end_dt, preserve_caps=True))
