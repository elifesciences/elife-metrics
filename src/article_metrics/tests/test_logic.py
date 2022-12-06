from unittest import mock
from os.path import join
from article_metrics import models, logic, utils
from datetime import datetime
from .base import BaseCase
import json
from article_metrics.scopus import citations as scopus_citations

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
        with mock.patch('article_metrics.crossref.citations.fetch', return_value=crossref_response):
            logic.import_crossref_citations()
            self.assertEqual(models.Citation.objects.count(), 1)
            self.assertEqual(models.Citation.objects.get(source=models.CROSSREF).num, expected_citations)

    def test_import_scopus_citations(self):
        search_results = json.load(open(join(self.fixture_dir, "scopus-responses", "dodgy-scopus-results.json"), "r"))
        fixture = scopus_citations.parse_result_page(search_results)
        # lsh@2022-10-17: `parse_result_page` is now lazy.
        # calling `len` on it to find the expected number of entries will fail,
        # calling `list` on it may skew the test,
        # calling `list` on it during the `expected` check will produce 0 as it has been consumed.
        # instead, read in a copy and then realise it with `list`.
        realised_fixture = list(scopus_citations.parse_result_page(search_results))
        with mock.patch("article_metrics.scopus.citations.all_todays_entries", return_value=fixture):
            logic.import_scopus_citations()

            unparseable_entries = 3
            unknown_doi_prefixes = 1
            subresource_dois = 2
            bad_eggs = unparseable_entries + unknown_doi_prefixes + subresource_dois
            expected = len(realised_fixture) - bad_eggs
            self.assertEqual(models.Article.objects.count(), expected)

class Two(BaseCase):
    def test_get_create_article(self):
        "article is created if doesn't exist"
        cases = [
            {'doi': '10.7554/eLife.01234'},
            {'doi': '10.7554/elife.01234'},
            {'doi': '10.7554/ELIFE.01234'},
        ]
        self.assertEqual(models.Article.objects.count(), 0)
        for row in cases:
            artobj = logic.get_create_article(row)
            self.assertEqual(artobj.doi, '10.7554/eLife.01234')
        self.assertEqual(models.Article.objects.count(), 1)

    def test_get_create_article_no_doi(self):
        "non-doi identifiers can be used"
        # one perfect article
        art1 = logic.get_create_article({'doi': '10.7554/eLife.01234', 'pmid': 1, 'pmcid': 2})
        self.assertEqual(1, models.Article.objects.count())

        # attempt to get/create same article
        art2 = logic.get_create_article({'pmid': 1})
        self.assertEqual(1, models.Article.objects.count())

        art3 = logic.get_create_article({'pmcid': 2})
        self.assertEqual(1, models.Article.objects.count())

        self.assertEqual(art1.id, art2.id)
        self.assertEqual(art2.id, art3.id)

class TestGAImport(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_import_ga_daily_stats(self):
        "ensure that a basic import of a day's worth of metrics happens correctly"
        self.assertEqual(0, models.Article.objects.count())
        day_to_import = datetime(year=2015, month=9, day=11)

        def test_output_path(result_type, from_date, to_date):
            # ignore whatever dates given, return path to fixture
            fixture = join(self.fixture_dir, 'test_import_ga_daily_stats', 'ga-output', 'views', '2015-09-11.json')
            return fixture

        with mock.patch('article_metrics.ga_metrics.core.output_path', new=test_output_path):
            logic.import_ga_metrics('daily', from_date=day_to_import, to_date=day_to_import, use_only_cached=True)
        # we know this day reveals this many articles
        # expected_article_count = 1090 # changed when we introduced POA articles
        #expected_article_count = 1119
        # expected_article_count = 1122 # ah - this day in history keeps getting more popular it seems.
        # 2017-01-18: I've put the results of this day into the fixtures so that
        # when it changes again in the future we can  see just what it changing
        # 2019-03-27: I've run the test without caching, grabbed what GA was returning and compared the two - identical.
        # it's a testamount to GA accuracy but doesn't explain what is happening here.
        # setting use_only_cached=True will stop the old code talking to GA.
        # returning the path to the fixture ensures only known data is being looked at
        expected_article_count = 1119
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
            'doi': '10.7554/eLife.00001',
            'source': models.GA,
        }
        logic.insert_row(ds1)
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(1, models.Metric.objects.count())
        clean_metric = models.Metric.objects.get(article__doi='10.7554/eLife.00001')
        self.assertEqual(0, clean_metric.pdf)

        expected_update = {
            'pdf': 1,
            'full': 0,
            'abstract': 0,
            'digest': 0,
            'period': 'day',
            'date': '2001-01-01',
            'doi': '10.7554/eLife.00001',
            'source': models.GA,
        }
        logic.insert_row(expected_update)
        self.assertEqual(1, models.Metric.objects.count())
        clean_metric = models.Metric.objects.get(article__doi='10.7554/eLife.00001')
        self.assertEqual(1, clean_metric.pdf)
