from os.path import join
from unittest import mock
from collections import OrderedDict
from django.test import Client
from django.core.urlresolvers import reverse
from article_metrics import models, logic
from datetime import datetime, timedelta
from article_metrics.ga_metrics.utils import ymd

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
                        # 'full': 525,
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

        def test_output_path(result_type, from_date, to_date):
            # ignore whatever dates given, return path to fixture
            if result_type == 'views':
                return join(self.fixture_dir, 'test_import_ga_daily_stats', 'ga-output', 'views', '2015-09-11.json')
            if result_type == 'downloads':
                return join(self.fixture_dir, 'test_import_ga_daily_stats', 'ga-output', 'downloads', '2015-09-11.json')

        with mock.patch('article_metrics.ga_metrics.core.output_path', new=test_output_path):
            logic.import_ga_metrics('daily', from_date=day_to_import, to_date=day_to_import, use_only_cached=True)

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
                    # }
                }),
                'monthly': OrderedDict({}),
                # 'total': {
                #    '2015-09-11': {
                #        'full': ....,
                #        'abstract': ...,
                #        'digest': ...,
                #    },
                # },
            },
        }

        url = reverse('api-article-metrics', kwargs={'doi': doi})
        resp = self.c.get(url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected_data, resp.data)

    def test_multiple_daily_data(self):
        from_date = datetime(year=2015, month=9, day=11)
        to_date = from_date + timedelta(days=1)

        def test_output_path(result_type, from_date, to_date):
            # from-date and to-date only differ on monthly requests
            assert from_date == to_date, "assumption about dates failed!"
            dt = ymd(from_date)
            if result_type == 'views':
                return join(self.fixture_dir, 'test_import_ga_multiple_daily_stats', 'views', dt + '.json')
            if result_type == 'downloads':
                return join(self.fixture_dir, 'test_import_ga_multiple_daily_stats', 'downloads', dt + '.json')

        with mock.patch('article_metrics.ga_metrics.core.output_path', new=test_output_path):
            logic.import_ga_metrics('daily', from_date, to_date, use_only_cached=True)

        doi = '10.7554/eLife.09560'

        # hack. the v1 api only queries the last 30 days and is not variable
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
