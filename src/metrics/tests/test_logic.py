import pytest
from . import base
from article_metrics.utils import tod
from metrics import logic, models
from datetime import date, timedelta
from unittest.mock import patch
from django.db.models import Sum

@pytest.mark.django_db
def test_no_nothing():
    "logic.page_views returns None when Page not found"
    expected = None
    pid, ptype = 'foo', 'event'
    assert expected == logic.page_views(pid, ptype)

@pytest.mark.django_db
def test_bad_metrics():
    "logic.page_views throws ValueError when we give it gibberish"
    for bad_pid in [1, {}, []]:
        for bad_ptype in [1, 'foo', {}, []]:
            for bad_period in [1, 'foo', {}, []]:
                with pytest.raises(ValueError):
                    logic.page_views(bad_pid, bad_ptype, bad_period)

@pytest.mark.django_db
def test_daily_metrics():
    "logic.page_views returns the sum of all daily hits and a chop'able queryset"
    fixture = [
        ('pants', 'event', '2016-01-01', 1),
        ('pants', 'event', '2016-01-02', 2),
        ('pants', 'event', '2016-01-03', 4),
        ('pants', 'event', '2016-01-04', 8)

        # it's obvious the pants event is exponentially popular
    ]
    base.insert_metrics(fixture)

    expected_sum = 15
    total, qobj = logic.page_views('pants', 'event', logic.DAY)
    assert total == expected_sum
    assert qobj.count() == len(fixture)

@pytest.mark.django_db
def test_monthly_metrics():
    "logic.page_views returns the sum of all monthly hits (same as sum of all daily hits) and a chop'able queryset"
    fixture = [
        ('pants', 'event', '2016-01-30', 1),
        ('pants', 'event', '2016-01-31', 2),
        ('pants', 'event', '2016-02-01', 3),
    ]
    base.insert_metrics(fixture)

    expected_sum = 6
    expected_result_count = 2 # results span two months
    total, qobj = logic.page_views('pants', 'event', logic.MONTH)
    assert total == expected_sum
    assert qobj.count() == expected_result_count

def test_interesting_frames():
    one_day = timedelta(days=1)
    one_moonth = timedelta(days=28)
    a = date(year=2017, month=1, day=1)
    b = a + one_moonth
    c = b + one_moonth
    d = c + one_moonth
    e = d + one_moonth
    f = e + one_moonth

    starts, ends = b + one_day, e - one_day

    frames = [
        {'starts': a, 'ends': b}, # outside of scope
        {'starts': b, 'ends': c}, # partially in scope
        {'starts': c, 'ends': d}, # completely in scope
        {'starts': d, 'ends': e}, # partially in scope
        {'starts': e, 'ends': f}, # outside of scope
    ]

    expected_frames = [
        {'starts': b, 'ends': c}, # partially in scope
        {'starts': c, 'ends': d}, # completely in scope
        {'starts': d, 'ends': e}, # partially in scope
    ]
    assert logic.interesting_frames(starts, ends, frames) == expected_frames

def test_aggregate():
    normalised_rows = logic.asmaps([
        ("/events/foo", tod("2018-01-01"), 1),
        ("/events/foo", tod("2018-01-02"), 2),

        ("/events/foo", tod("2018-01-03"), 2),
        ("/events/bar", tod("2018-01-03"), 1),
        ("/events/foo", tod("2018-01-03"), 2),
    ])

    # rows are sorted by date+path desc.
    # this means '2018-01-03' comes before '2018-01-02' and 'f' comes before 'b'
    expected_result = logic.asmaps([
        ("/events/foo", tod("2018-01-03"), 4), # aggregated row
        ("/events/bar", tod("2018-01-03"), 1),
        ("/events/foo", tod("2018-01-02"), 2),
        ("/events/foo", tod("2018-01-01"), 1),
    ])
    assert logic.aggregate(normalised_rows) == expected_result

@pytest.mark.django_db
def test_insert():
    assert models.Page.objects.count() == 0
    assert models.PageType.objects.count() == 0
    assert models.PageCount.objects.count() == 0

    aggregated_rows = logic.asmaps([
        ("/events/foo", tod("2018-01-01"), 1),
        ("/events/foo", tod("2018-01-02"), 2),
        ("/events/foo", tod("2018-01-03"), 4),
        ("/events/bar", tod("2018-01-03"), 1)
    ])
    results = logic.update_page_counts(models.EVENT, aggregated_rows)
    assert len(results) == len(aggregated_rows)

    assert models.PageType.objects.count() == 1
    assert models.Page.objects.count() == 2
    assert models.PageCount.objects.count() == 4

@pytest.mark.django_db
def test_double_insert():
    aggregated_rows = logic.asmaps([
        ("/events/foo", tod("2018-01-01"), 1),
        ("/events/foo", tod("2018-01-02"), 2),
        ("/events/foo", tod("2018-01-03"), 4),
        ("/events/bar", tod("2018-01-03"), 1)
    ])
    results = logic.update_page_counts(models.EVENT, aggregated_rows)
    assert len(results) == len(aggregated_rows)
    assert models.PageType.objects.count() == 1
    assert models.Page.objects.count() == 2
    assert models.PageCount.objects.count() == 4
    expected_total = 8
    actual_total = lambda: models.PageCount.objects.aggregate(total=Sum('views'))['total']
    assert expected_total == actual_total()

    # increase the view count, insert again.
    aggregated_rows = logic.asmaps([
        ("/events/foo", tod("2018-01-01"), 2),
        ("/events/foo", tod("2018-01-02"), 4),
        ("/events/foo", tod("2018-01-03"), 8),
        ("/events/bar", tod("2018-01-03"), 2)
    ])
    results = logic.update_page_counts(models.EVENT, aggregated_rows)
    assert len(results) == len(aggregated_rows)

    # these numbers should have stayed the same
    assert models.PageType.objects.count() == 1
    assert models.Page.objects.count() == 2
    assert models.PageCount.objects.count() == 4

    # but this should reflect the new total
    expected_total = 16
    assert expected_total == actual_total()

@pytest.mark.django_db
def test_update_ptype():
    "`update_ptype` convenience function behaves as expected"
    assert models.Page.objects.count() == 0
    assert models.PageType.objects.count() == 0
    assert models.PageCount.objects.count() == 0

    fixture = base.fixture_json('ga-response-events-frame2.json')

    frame = {'id': '2', 'prefix': '/events'}
    frame_query_list = [(frame, [{}])]
    with patch('metrics.logic.build_ga_query', return_value=frame_query_list):
        with patch('metrics.logic.query_ga', return_value=fixture):
            logic.update_ptype(models.EVENT)

    assert models.Page.objects.count() == 13
    assert models.PageType.objects.count() == 1 # 'event'
    # not the same as len(fixture.rows) because of aggregation
    assert models.PageCount.objects.count() == 138

def test_build_ga_query__invalid_dates_dropped():
    today = date(year=2015, month=6, day=1)
    invalid_cases = [
        # yesterday, invalid
        (date(year=2015, month=5, day=31), date(year=2015, month=5, day=31)),
        # today, invalid
        (date(year=2015, month=6, day=1), date(year=2015, month=6, day=1)),
        # tomorrow, invalid
        (date(year=2015, month=6, day=2), date(year=2015, month=6, day=2)),
    ]
    with patch('metrics.logic.date_today', return_value=today):
        for start_date, end_date in invalid_cases:
            frame = logic.build_ga_query(models.EVENT, start_date, end_date)
            assert frame == []

def test_build_ga_query__invalid_date_ranges_truncated():
    # start of year to today is truncated to day before yesterday
    today = date(year=2015, month=6, day=1)
    start_date = date(year=2015, month=1, day=1)
    invalid_cases = [
        # yesterday
        date(year=2015, month=5, day=31),
        # today
        date(year=2015, month=6, day=1),
        # tomorrow
        date(year=2015, month=6, day=2),
    ]
    expected_end_date = date(year=2015, month=5, day=30)
    with patch('metrics.logic.date_today', return_value=today):
        for end_date in invalid_cases:
            query_list = logic.build_ga_query(models.EVENT, start_date, end_date)
            assert len(query_list) == 1 # one interesting frame
            frame, query = query_list[0]
            assert query['end_date'] == expected_end_date
