import pytest
from datetime import date
from metrics import history, models
from article_metrics.utils import date_today
from django.conf import settings

def test_history_gets_dates_capped():
    case = {
        'judgement-day': {
            'frames': [
                {'id': 1,
                 'starts': date(year=1997, month=8, day=29),
                 'ends': None, # becomes date_today()
                 'pattern': '.*$'},
                {'id': 2,
                 'starts': None, # becomes settings.INCEPTION
                 'ends': date(year=1997, month=8, day=28),
                 'pattern': 'life-as-we-know-it'}
            ],
        }
    }
    results = history.type_history.validate(case)
    assert results['judgement-day']['frames'][0]['ends'] == date_today()
    assert results['judgement-day']['frames'][-1]['starts'] == settings.INCEPTION.date()

def test_history_frames_sorted():
    d1 = date(year=2018, month=1, day=1)
    d2 = date(year=2018, month=2, day=2)
    d3 = date(year=2018, month=3, day=3)
    d4 = date(year=2018, month=4, day=4)

    f1 = {'id': 'f1', 'starts': d1, 'ends': d2, 'pattern': 'na'}
    f2 = {'id': 'f2', 'starts': d2, 'ends': d3, 'pattern': 'na'}
    f3 = {'id': 'f3', 'starts': d3, 'ends': d4, 'pattern': 'na'}

    case = {'foo': {'frames': [f2, f3, f1]}}
    results = history.type_history.validate(case)
    assert results['foo']['frames'][0]['starts'] == d1
    assert results['foo']['frames'][-1]['ends'] == d4

def test_history_frames_sorted_uncapped():
    d2 = date(year=2018, month=2, day=2)
    d3 = date(year=2018, month=3, day=3)

    f1 = {'id': 'f1', 'starts': None, 'ends': d2, 'pattern': 'na'}
    f2 = {'id': 'f2', 'starts': d2, 'ends': d3, 'pattern': 'na'}
    f3 = {'id': 'f3', 'starts': d3, 'ends': None, 'pattern': 'na'}

    case = {'foo': {'frames': [f2, f3, f1]}}
    results = history.type_history.validate(case)
    assert results['foo']['frames'][0]['starts'] == settings.INCEPTION.date()
    assert results['foo']['frames'][-1]['ends'] == date_today()

def test_default_history_file():
    history.load_history() # no SchemaError errors thrown

def test_load_ptype_history():
    history.ptype_history(models.EVENT)

def test_load_missing_ptype_history():
    with pytest.raises(ValueError):
        history.ptype_history("pants")
