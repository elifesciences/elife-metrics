from datetime import date
from . import base
from metrics import history, models
from django.conf import settings

class One(base.BaseCase):

    def test_history_gets_dates_capped(self):
        case = {
            'judgement-day': {
                'frames': [
                    {'id': 1,
                     'starts': str(date(year=1997, month=8, day=29)),
                     'ends': None, # becomes date.today()
                     'pattern': '.*$'},
                    {'id': 2,
                     'starts': None, # becomes settings.INCEPTION
                     'ends': str(date(year=1997, month=8, day=28)),
                     'pattern': 'life-as-we-know-it'}
                ],
            }
        }
        history.validate_history_data(case)
        results = history.coerce_history_data(case)
        self.assertEqual(results['judgement-day']['frames'][0]['ends'], date.today())
        self.assertEqual(results['judgement-day']['frames'][-1]['starts'], settings.INCEPTION.date())

    def test_history_frames_sorted(self):
        d1 = date(year=2018, month=1, day=1)
        d2 = date(year=2018, month=2, day=2)
        d3 = date(year=2018, month=3, day=3)
        d4 = date(year=2018, month=4, day=4)

        f1 = {'id': 'f1', 'starts': str(d1), 'ends': str(d2), 'pattern': 'na'}
        f2 = {'id': 'f2', 'starts': str(d2), 'ends': str(d3), 'pattern': 'na'}
        f3 = {'id': 'f3', 'starts': str(d3), 'ends': str(d4), 'pattern': 'na'}

        case = {'foo': {'frames': [f2, f3, f1]}}
        history.validate_history_data(case)
        results = history.coerce_history_data(case)
        self.assertEqual(results['foo']['frames'][0]['starts'], d1)
        self.assertEqual(results['foo']['frames'][-1]['ends'], d4)

    def test_history_frames_sorted_uncapped(self):
        d2 = date(year=2018, month=2, day=2)
        d3 = date(year=2018, month=3, day=3)

        f1 = {'id': 'f1', 'starts': None, 'ends': d2, 'pattern': 'na'}
        f2 = {'id': 'f2', 'starts': d2, 'ends': d3, 'pattern': 'na'}
        f3 = {'id': 'f3', 'starts': d3, 'ends': None, 'pattern': 'na'}

        case = {'foo': {'frames': [f2, f3, f1]}}
        history.validate_history_data(case)
        results = history.coerce_history_data(case)
        self.assertEqual(results['foo']['frames'][0]['starts'], settings.INCEPTION.date())
        self.assertEqual(results['foo']['frames'][-1]['ends'], date.today())

    def test_default_history_file(self):
        history.load_from_file() # no SchemaError errors thrown

    def test_load_ptype_history(self):
        history.ptype_history(models.EVENT)

    def test_load_missing_ptype_history(self):
        self.assertRaises(ValueError, history.ptype_history, "pants")
