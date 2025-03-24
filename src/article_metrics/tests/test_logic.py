import pathlib
from typing import Iterator
from unittest import mock
from article_metrics import models, logic, utils
from datetime import datetime
from . import base
from article_metrics.scopus import citations as scopus_citations
import pytest


@pytest.fixture(name='citations_for_all_articles_mock')
def _citations_for_all_articles_mock() -> Iterator[mock.MagicMock]:
    with mock.patch('article_metrics.crossref.citations.citations_for_all_articles') as _mock:
        yield _mock


class TestImportCrossrefCitations:
    def test_pass_msid_to_citations_for_all_articles(
        self,
        citations_for_all_articles_mock: mock.MagicMock
    ):
        logic.import_crossref_citations(msid='12345')
        citations_for_all_articles_mock.assert_called_with(msid='12345')


@pytest.mark.django_db
def test_import_crossref_citations():
    # crossref requires an article to exist before we scrape it
    utils.create_or_update(models.Article, {'doi': '10.7554/eLife.09560'}, ['doi'])
    assert models.Article.objects.count() == 1
    assert models.Citation.objects.count() == 0

    crossref_response = pathlib.Path(base.fixture_path("crossref-request-response.xml")).read_text()
    expected_citations = 53
    with mock.patch('article_metrics.crossref.citations.fetch', side_effect=[crossref_response]):
        with mock.patch('article_metrics.utils.get_article_versions', return_value=[]):
            logic.import_crossref_citations()
            assert models.Citation.objects.count() == 1
            assert models.Citation.objects.get(source=models.CROSSREF).num == expected_citations

@pytest.mark.django_db
def test_import_crossref_citations_for_multiple_versions():
    utils.create_or_update(models.Article, {'doi': '10.7554/eLife.09560'}, ['doi'])
    assert models.Article.objects.count() == 1
    assert models.Citation.objects.count() == 0

    crossref_response_1 = pathlib.Path(base.fixture_path("crossref-request-response.xml")).read_text()
    crossref_response_2 = pathlib.Path(base.fixture_path("crossref-request-response-2.xml")).read_text()
    crossref_response_3 = pathlib.Path(base.fixture_path("crossref-request-response-3.xml")).read_text()
    expected_citations = 66 # 53 (umbrella) + 3 (v1) + 10 (v2)
    with mock.patch('article_metrics.crossref.citations.fetch',
                    side_effect=[crossref_response_1, crossref_response_2, crossref_response_3]):
        with mock.patch('article_metrics.utils.get_article_versions', return_value=[1, 2]):
            logic.import_crossref_citations()
            assert models.Citation.objects.count() == 1
            assert models.Citation.objects.get(source=models.CROSSREF).num == expected_citations

@pytest.mark.django_db
def test_import_scopus_citations():
    search_results = base.fixture_json("scopus-responses/dodgy-scopus-results.json")
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
        assert expected == models.Article.objects.count()

@pytest.mark.django_db
def test_get_create_article():
    "article is created if doesn't exist"
    cases = [
        {'doi': '10.7554/eLife.01234'},
        {'doi': '10.7554/elife.01234'},
        {'doi': '10.7554/ELIFE.01234'},
    ]
    assert models.Article.objects.count() == 0
    for row in cases:
        artobj = logic.get_create_article(row)
        assert artobj.doi == '10.7554/eLife.01234'
    assert models.Article.objects.count() == 1

@pytest.mark.django_db
def test_get_create_article_no_doi():
    "non-doi identifiers can be used"
    # one perfect article
    art1 = logic.get_create_article({'doi': '10.7554/eLife.01234', 'pmid': 1, 'pmcid': 2})
    assert models.Article.objects.count() == 1

    # attempt to get/create same article
    art2 = logic.get_create_article({'pmid': 1})
    assert models.Article.objects.count() == 1

    art3 = logic.get_create_article({'pmcid': 2})
    assert models.Article.objects.count() == 1

    assert art1.id == art2.id
    assert art2.id == art3.id

# --- GA import

@pytest.mark.django_db
def test_import_ga_daily_stats():
    "ensure that a basic import of a day's worth of metrics happens correctly"
    assert models.Article.objects.count() == 0
    day_to_import = datetime(year=2015, month=9, day=11)

    fixture = base.fixture_path('test_import_ga_daily_stats/ga-output/views/2015-09-11.json')
    with mock.patch('article_metrics.ga_metrics.core.output_path_v2', return_value=fixture):
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
    assert expected_article_count == models.Article.objects.count()

@pytest.mark.django_db
def test_data_is_updated():
    "ensure data is updated correctly"
    assert models.Article.objects.count() == 0
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

    # rows were created
    assert models.Article.objects.count() == 1
    assert models.Metric.objects.count() == 1

    # rows have correct values
    clean_metric = models.Metric.objects.get(article__doi='10.7554/eLife.00001')
    assert clean_metric.pdf == 0

    # update row
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

    # no extra rows were created
    assert models.Metric.objects.count() == 1

    # rows have correct values
    clean_metric = models.Metric.objects.get(article__doi='10.7554/eLife.00001')
    assert clean_metric.pdf == 1
