from datetime import date
from . import base
from metrics import history, models
from django.conf import settings

class One(base.BaseCase):
    def test_frame(self):
        today = date.today()
        cases = [
            (history.frame0, {'starts': None, 'ends': today}),
            (history.frame0, {'starts': today, 'ends': None}),
            (history.frame0, {'starts': today, 'ends': today}),

            (history.frame1, {'starts': today, 'ends': None, 'prefix': '/pants'}),
            (history.frame1, {'starts': None, 'ends': today, 'prefix': '/pants'}),

            (history.frame2, {'starts': today, 'ends': None, 'prefix': '/pants', 'path-list': ['p1']}),
            (history.frame2, {'starts': None, 'ends': today, 'prefix': '/pants', 'path-list': ['p2']}),

            (history.frame3, {'starts': today, 'ends': None, 'pattern': 'party'}),
            (history.frame3, {'starts': None, 'ends': today, 'pattern': 'party'}),
        ]
        for schema, case in cases:
            with self.subTest():
                schema.validate(case)

        # all of the above variations (except frame0) are collected under `history.frame`
        for case in map(lambda p: p[1], cases[3:]):
            with self.subTest(case):
                history.type_frame.validate(case)

    def test_history(self):
        case = {
            'judgement-day': {
                'frames': [
                    {'starts': date(year=1997, month=8, day=29),
                     'ends': None,
                     'pattern': '.*$'}
                ],
                'examples': [
                    'terminator',
                    't2: judgement day',
                ]
            }
        }
        history.type_history.validate(case)

    def test_history_gets_dates_capped(self):
        case = {
            'judgement-day': {
                'frames': [
                    {'starts': date(year=1997, month=8, day=29),
                     'ends': None, # becomes date.today()
                     'pattern': '.*$'},
                    {'starts': None, # becomes settings.INCEPTION
                     'ends': date(year=1997, month=8, day=28),
                     'pattern': 'life-as-we-know-it'}
                ],
                'examples': [
                    'terminator',
                    't2: judgement day',
                ]
            }
        }
        results = history.type_history.validate(case)
        self.assertEqual(results['judgement-day']['frames'][0]['ends'], date.today())
        self.assertEqual(results['judgement-day']['frames'][-1]['starts'], settings.INCEPTION.date())

    def test_default_history_file(self):
        history.load_from_file() # no SchemaError errors thrown

    def test_load_ptype_history(self):
        history.ptype_history(models.EVENT)

    def test_load_missing_ptype_history(self):
        self.assertRaises(ValueError, history.ptype_history, "pants")
