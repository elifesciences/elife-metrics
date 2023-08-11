from . import base
from metrics import models, views, logic, history
from article_metrics import utils
from django.urls import reverse
from django.test import Client
import pytest

@pytest.mark.django_db
def test_request_empty_db():
    "regular requests fail with a 404 when the database is empty"
    dummy_pid_list = ['foo', 'bar', 'baz', 1, 2, 3]
    client = Client()
    for pid in dummy_pid_list:
        for ptype in models.PAGE_TYPES: # press-packages, etc
            url = reverse(views.metrics, kwargs={'ptype': ptype, 'pid': pid})
            for period in [logic.DAY, logic.MONTH]:
                resp = client.get(url, {'by': period})
                assert resp.status_code == 404

@pytest.mark.django_db
def test_request_day_periods():
    # populate db
    fixture = base.fixture_json('ga-response-events-frame2.json')
    frame = {'id': '2', 'prefix': '/events'}
    rows = logic.aggregate(logic.process_response(models.EVENT, frame, fixture))
    logic.update_page_counts(models.EVENT, rows)
    client = Client()

    url = reverse(views.metrics, kwargs={'ptype': models.EVENT})
    resp = client.get(url, {'by': logic.DAY})
    assert resp.status_code == 200

    expected = {
        'periods': [
            {'period': '2018-01-31', 'value': 2},
            {'period': '2018-01-30', 'value': 5},
            {'period': '2018-01-29', 'value': 9},
            {'period': '2018-01-26', 'value': 1},
            {'period': '2018-01-25', 'value': 5},
            {'period': '2018-01-24', 'value': 6},
            {'period': '2018-01-23', 'value': 4},
            {'period': '2018-01-22', 'value': 1},
            {'period': '2018-01-19', 'value': 3},
            {'period': '2018-01-18', 'value': 1},
            {'period': '2018-01-17', 'value': 2},
            {'period': '2018-01-16', 'value': 7},
            {'period': '2018-01-15', 'value': 3},
            {'period': '2018-01-12', 'value': 2},
            {'period': '2018-01-11', 'value': 10},
            {'period': '2018-01-10', 'value': 3},
            {'period': '2018-01-09', 'value': 3},
            {'period': '2018-01-08', 'value': 2},
            {'period': '2018-01-05', 'value': 1},
            {'period': '2018-01-04', 'value': 5}],
        'totalPeriods': 22,
        'totalValue': 79}

    assert expected == resp.json()

@pytest.mark.django_db
def test_request_month_periods():
    # populate db
    fixture = base.fixture_json('ga-response-events-frame2.json')
    frame = {'id': '2', 'prefix': '/events'}
    rows = logic.aggregate(logic.process_response(models.EVENT, frame, fixture))
    logic.update_page_counts(models.EVENT, rows)
    client = Client()

    url = reverse(views.metrics, kwargs={'ptype': models.EVENT})
    resp = client.get(url, {'by': logic.MONTH})
    assert resp.status_code == 200
    expected = {
        'periods': [
            {'period': '2018-01', 'value': 79},
        ],
        'totalPeriods': 1,
        'totalValue': 79
    }
    assert expected == resp.json()

@pytest.mark.django_db
def test_content_types():
    "ensure all content types in history schema"
    client = Client()
    spec_content_types = history.load_history().keys()

    # create a page "asdf" for every content type in history file
    # this itself may fail if models.PAGE_TYPES hasn't been updated
    dummy_id = "asdf"
    for sct in spec_content_types:
        ptype, _, _ = utils.create_or_update(models.PageType, {"name": sct}, update=False)
        utils.create_or_update(models.Page, {"type": ptype, "identifier": dummy_id})

    expected = {'periods': [], 'totalPeriods': 0, 'totalValue': 0}
    for sct in spec_content_types:
        resp = client.get(reverse(views.metrics, kwargs={'ptype': sct, 'pid': dummy_id}))
        assert resp.status_code == 200
        assert expected == resp.json()
