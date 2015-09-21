from collections import OrderedDict
from django.test import TestCase, Client
from django.core.urlresolvers import reverse
from metrics import models, logic
from datetime import datetime

class BaseCase(TestCase):
    def __init__(self, *args, **kwargs):
        super(BaseCase, self).__init__(*args, **kwargs)
        self.maxDiff = None


class TestGAImport(BaseCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass

    def test_import_ga_daily_stats(self):
        "ensure that a basic import of a day's worth of metrics happens correctly"
        self.assertEqual(0, models.Article.objects.count())
        day_to_import = datetime(year=2015, month=9, day=11)
        logic.import_ga_metrics(from_date=day_to_import, to_date=day_to_import)
        expected_article_count = 1090 # we know this day reveals this many articles
        self.assertEqual(expected_article_count, models.Article.objects.count())


class TestHWImport(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_import_hw_monthly_stats(self):
        self.assertEqual(0, models.Article.objects.count())
        day_to_import = datetime(year=2015, month=8, day=11)
        logic.import_hw_metrics('monthly', from_date=day_to_import, to_date=day_to_import)
        expected_article_count = 1631
        self.assertEqual(expected_article_count, models.Article.objects.count())

        doi = '10.7554/eLife.02993'
        expected_data = {
            'abstract': 2,
            'date': '2015-08',
            'full': 26,
            'pdf': 18,
            'period': 'month',
        }
        metric = models.Metric.objects.get(article__doi=doi, period='month', date='2015-08')
        for attr, val in expected_data.items():
            self.assertEqual(expected_data[attr], getattr(metric, attr))
        

    def test_import_hw_daily_stats(self):
        self.assertEqual(0, models.Article.objects.count())
        day_to_import = datetime(year=2015, month=8, day=11)
        logic.import_hw_metrics('daily', from_date=day_to_import, to_date=day_to_import)
        expected_article_count = 11
        self.assertEqual(expected_article_count, models.Article.objects.count())

        doi = '10.7554/eLife.02993'
        expected_data = {
            'abstract': 0,
            'date': '2015-08-11',
            'full': 1,
            'pdf': 2,
            'period': 'day',
        }
        metric = models.Metric.objects.get(article__doi=doi, period='day', date='2015-08-11')
        for attr, val in expected_data.items():
            self.assertEqual(expected_data[attr], getattr(metric, attr))

    


class TestAPI(BaseCase):
    def setUp(self):
        self.c = Client()

    def tearDown(self):
        pass

    def test_monthly_import(self):
        self.assertEqual(0, models.Article.objects.count())
        self.assertEqual(0, models.Metric.objects.count())
        month_to_import = datetime(year=2015, month=8, day=01)
        logic.import_ga_metrics('monthly', from_date=month_to_import, to_date=month_to_import)
        expected = 1649
        self.assertEqual(expected, models.Article.objects.count())
        self.assertEqual(expected, models.Metric.objects.count())

        doi = '10.7554/eLife.08007'
        
        expected_data = {
            doi: {
                'monthly': OrderedDict({
                    '2015-08': {
                        'full': 525,
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
        data = resp.data
        del data[doi]['daily'] # too many, not being tested
        self.assertEqual(expected_data, resp.data)

    def test_daily_import(self):
        "a very simple set of data returns the expected daily and monthly data in the expected structure"
        day_to_import = datetime(year=2015, month=9, day=11)
        logic.import_ga_metrics('daily', from_date=day_to_import, to_date=day_to_import)
        doi = '10.7554/eLife.09560'
        expected_data = {
            doi: {
                'daily': OrderedDict({
                    '2015-09-11': {
                        'full': 21922,
                        'abstract': 325,
                        'digest': 114,
                        'pdf': 1533,
                    },
                    #2015-09-12: {
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
