from collections import OrderedDict
from django.test import Client
from django.core.urlresolvers import reverse
from metrics import models, logic
from datetime import datetime, timedelta
from metrics.ga_metrics.utils import ymd

from base import BaseCase

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
        # we know this day reveals this many articles
        # expected_article_count = 1090 # changed when we introduced POA articles
        #expected_article_count = 1119
        expected_article_count = 1122 # ah - this day in history keeps getting more popular it seems.
        # 2017-01-18: I've put the results of this day into the fixtures so that
        # when it changes again in the future we can  see just what it changing
        self.assertEqual(expected_article_count, models.Article.objects.count())

    def test_partial_data_is_updated(self):
        "ensure that any partial data is updated correctly when detected"
        self.assertEqual(0, models.Article.objects.count())
        ds1 = {
            'pdf': 0,
            'full': 0,
            'abstract': 0,
            'digest': 0,
            'period': 'day',
            'date': '2001-01-01',
            'doi': '10.7554/DUMMY',
        }
        logic.insert_row(ds1)
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(1, models.Metric.objects.count())
        clean_metric = models.Metric.objects.get(article__doi='10.7554/DUMMY')
        self.assertEqual(0, clean_metric.pdf)

        expected_update = {
            'pdf': 1,
            'full': 0,
            'abstract': 0,
            'digest': 0,
            'period': 'day',
            'date': '2001-01-01',
            'doi': '10.7554/DUMMY',
        }
        logic.insert_row(expected_update)
        self.assertEqual(1, models.Metric.objects.count())
        clean_metric = models.Metric.objects.get(article__doi='10.7554/DUMMY')
        self.assertEqual(1, clean_metric.pdf)

'''
class TestHWImport(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_import_hw_monthly_stats(self):
        self.assertEqual(0, models.Article.objects.count())
        day_to_import = datetime(year=2015, month=8, day=11)
        logic.import_hw_metrics('monthly', from_date=day_to_import, to_date=day_to_import)
        # 2015-11-20, HW stats can't be trusted. I don't know why there are suddenly fewer
        # articles on this day now that we have more data...
        #expected_article_count = 1631

        #expected_article_count = 1603
        # 2016-02-16: aaaaand we're back to 1631
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

        # 2015-11-20, new article present after supporting multiple datasets in elife-hw-metrics
        #expected_article_count = 11
        expected_article_count = 12
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
'''


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
        doi = u'10.7554/eLife.09560'

        # hack.
        yesterday = unicode(ymd(datetime.now() - timedelta(days=1)))
        day_before = unicode(ymd(datetime.now() - timedelta(days=2)))
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
