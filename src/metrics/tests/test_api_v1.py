from collections import OrderedDict
from django.test import Client
from django.core.urlresolvers import reverse
from metrics import models, logic
from datetime import datetime, timedelta
from metrics.ga_metrics.utils import ymd

from .base import BaseCase

class TestAPI(BaseCase):
    def setUp(self):
        self.c = Client()

    def tearDown(self):
        pass

    def test_monthly_data(self):
        self.assertEqual(0, models.Article.objects.count())
        self.assertEqual(0, models.Metric.objects.count())
        month_to_import = datetime(year=2015, month=8, day=0o1)
        logic.import_ga_metrics('monthly', from_date=month_to_import, to_date=month_to_import)
        expected = 1649
        self.assertEqual(expected, models.Article.objects.count())
        self.assertEqual(expected, models.Metric.objects.count())

        doi = '10.7554/eLife.08007'

        metrics = models.Metric.objects.get(article__doi=doi)
        this_month = ymd(datetime.now() - timedelta(days=1))[:-3]
        metrics.date = this_month
        metrics.save()

        expected_data = {
            doi: {
                'daily': OrderedDict({}),
                'monthly': OrderedDict({
                    this_month: {
                        #'full': 525,
                        'full': 604, # introduction of POA as full text views
                        'abstract': 9,
                        'digest': 46,
                        'pdf': 129,
                    },
                }),
            },
        }
        url = reverse('api-article-metrics', kwargs={'doi': doi})
        resp = self.c.get(url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected_data, resp.data)

    def test_daily_data(self):
        "a very simple set of data returns the expected daily and monthly data in the expected structure"
        day_to_import = datetime(year=2015, month=9, day=11)
        logic.import_ga_metrics('daily', from_date=day_to_import, to_date=day_to_import)

        doi = '10.7554/eLife.09560'

        # hack.
        metric = models.Metric.objects.get(article__doi=doi)
        yesterday = ymd(datetime.now() - timedelta(days=1))
        metric.date = yesterday
        metric.save()

        expected_data = {
            doi: {
                'daily': OrderedDict({
                    yesterday: {
                        'full': 21922,
                        'abstract': 325,
                        'digest': 114,
                        'pdf': 1533,
                    },
                    # 2015-09-12: {
                    #    ....
                    #
                    #}
                }),
                'monthly': OrderedDict({}),
                #'total': {
                #    '2015-09-11': {
                #        'full': ....,
                #        'abstract': ...,
                #        'digest': ...,
                #    },
                #},
            },
        }

        url = reverse('api-article-metrics', kwargs={'doi': doi})
        resp = self.c.get(url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected_data, resp.data)

    def test_multiple_daily_data(self):
        from_date = datetime(year=2015, month=9, day=11)
        to_date = from_date + timedelta(days=1)
        logic.import_ga_metrics('daily', from_date, to_date)
        doi = '10.7554/eLife.09560'

        # hack.
        yesterday = str(ymd(datetime.now() - timedelta(days=1)))
        day_before = str(ymd(datetime.now() - timedelta(days=2)))
        m1, m2 = models.Metric.objects.filter(article__doi=doi)
        m1.date = day_before
        m2.date = yesterday
        m1.save()
        m2.save()

        expected_data = {
            doi: {
                'daily': OrderedDict([
                    (day_before, {
                        'full': 21922,
                        'abstract': 325,
                        'digest': 114,
                        'pdf': 1533,
                    }),
                    (yesterday, {
                        'full': 9528,
                        'abstract': 110,
                        'digest': 42,
                        'pdf': 489,
                    })
                ]),
                'monthly': OrderedDict({})
            },
        }
        url = reverse('api-article-metrics', kwargs={'doi': doi})
        resp = self.c.get(url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected_data, resp.data)

'''
class TestMultiSourceAPI(BaseCase):
    def setUp(self):
        self.c = Client()

    def tearDown(self):
        pass

    def test_mixed_source_data(self):
        "data from multiple sources is served up correctly"
        from_date = datetime(year=2015, month=9, day=11)
        to_date = from_date + timedelta(days=1)
        logic.import_ga_metrics('daily', from_date, to_date)
        logic.import_hw_metrics('daily', from_date, to_date)
        doi = '10.7554/eLife.09560'


        # hack.
        yesterday = ymd(datetime.now() - timedelta(days=1))
        day_before = ymd(datetime.now() - timedelta(days=2))
        m1, m2 = models.Metric.objects.filter(article__doi=doi, source=models.GA)
        m1.date = day_before
        m2.date = yesterday
        m1.save()
        m2.save()

        m1, m2 = models.Metric.objects.filter(article__doi=doi, source=models.HW)
        m1.date = day_before
        m2.date = yesterday
        m1.save()
        m2.save()

        expected_data = {
            models.GA: {
                doi: {
                    'daily': OrderedDict([
                        (day_before, {
                            'full': 21922,
                            'abstract': 325,
                            'digest': 114,
                            'pdf': 1533,
                        }),
                        (yesterday, {
                            'full': 9528,
                            'abstract': 110,
                            'digest': 42,
                            'pdf': 489,
                        })
                    ]),
                    'monthly': OrderedDict({}),
                },
            },
            models.HW: {
                doi: {
                    'daily': OrderedDict([
                        (day_before, {
                            'full': 39912,
                            'abstract': 540,
                            'digest': 0,
                            'pdf': 4226,
                        }),
                        (yesterday, {
                            'full': 15800,
                            'abstract': 144,
                            'digest': 0,
                            'pdf': 1132,
                        }),
                    ]),
                    'monthly': OrderedDict({}),
                },
            },
        }
        url = reverse('api-article-metrics-mixed-source', kwargs={'doi': doi})
        resp = self.c.get(url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected_data, resp.data)
'''
