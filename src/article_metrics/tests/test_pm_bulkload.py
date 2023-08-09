from django.conf import settings
from article_metrics.pm import bulkload_pmids
from . import base
from article_metrics import models
import pytest

@pytest.mark.django_db
def test_load():
    assert models.Article.objects.count() == 0
    fixture = base.fixture_path('pm-fixture.csv')
    bulkload_pmids.load_csv(fixture)
    assert models.Article.objects.count() == 9
    for art in models.Article.objects.all():
        assert art.pmid
        assert art.pmcid
        assert art.doi
        assert art.doi.startswith('10.7554/eLife.')

@pytest.mark.django_db
def test_load_missing():
    "missing values in csv don't prevent load"
    assert models.Article.objects.count() == 0
    doi = settings.DOI_PREFIX + '/eLife.123456'
    pmcid = '7890123'
    row = {
        'DOI': doi,
        'PMCID': pmcid,
        'PMID': ''
    }
    bulkload_pmids.update_article(row)
    assert models.Article.objects.count() == 1
    art = models.Article.objects.get(doi=doi)
    assert art.pmid is None
    assert art.pmcid == pmcid
