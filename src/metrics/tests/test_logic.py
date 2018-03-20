from unittest import mock
from os.path import join
from metrics import models, logic, utils
from datetime import datetime
from .base import BaseCase
import json
from metrics.scopus import citations as scopus_citations

class One(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_import_crossref_citations(self):
        # crossref requires an article to exist before we scrape it
        utils.create_or_update(models.Article, {'doi': '10.7554/eLife.09560'}, ['doi'])
        self.assertEqual(models.Article.objects.count(), 1)
        self.assertEqual(models.Citation.objects.count(), 0)

        crossref_response = open(join(self.fixture_dir, "crossref-request-response.xml"), 'r').read()
        expected_citations = 53
        with mock.patch('metrics.crossref.citations.fetch', return_value=crossref_response):
            logic.import_crossref_citations()
            self.assertEqual(models.Citation.objects.count(), 1)
            self.assertEqual(models.Citation.objects.get(source=models.CROSSREF).num, expected_citations)

    def test_import_scopus_citations(self):
        search_results = json.load(open(join(self.fixture_dir, "scopus-responses", "dodgy-scopus-results.json"), "r"))
        fixture = scopus_citations.parse_results(search_results)
        with mock.patch("metrics.scopus.citations.all_todays_entries", return_value=fixture):
            logic.import_scopus_citations()


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
            'source': models.GA,
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
            'source': models.GA,
        }
        logic.insert_row(expected_update)
        self.assertEqual(1, models.Metric.objects.count())
        clean_metric = models.Metric.objects.get(article__doi='10.7554/DUMMY')
        self.assertEqual(1, clean_metric.pdf)
