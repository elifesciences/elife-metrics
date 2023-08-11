import os
import json
from article_metrics import utils, models, logic
from datetime import timedelta, datetime
import pytest

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
BASE_DATE = datetime(year=2001, month=1, day=1)
FIXTURE_DIR = os.path.join(THIS_DIR, 'fixtures')

def fixture_path(fixture_name):
    path = os.path.join(FIXTURE_DIR, fixture_name)
    utils.ensure(os.path.exists(path), "fixture not found: %s" % path)
    return path

def fixture_json(fixture_name):
    "returns the contents of `fixture_name` as JSON"
    with open(fixture_path(fixture_name), 'r') as fh:
        return json.load(fh)

def insert_metrics(abbr_list):
    "function to bypass scraping logic and insert metrics and citations directly into db"
    def wrangle(msid, data, date):
        full = abstract = digest = pdf = 0
        citations = [0]
        period = models.DAY

        if len(data) == 3:
            citations, pdf, full = data
        elif len(data) == 4:
            citations, pdf, full, period = data
        else:
            raise ValueError("cannot handle row of length %s" % len(data))

        # allows us to pass in a triple for better testing
        if isinstance(full, int):
            full = [full, abstract, digest]
        full, abstract, digest = full

        # format date
        fn = utils.ym if period == models.MONTH else utils.ymd
        date = fn(date)

        metric = logic.insert_row({
            'doi': utils.msid2doi(msid),
            'date': date,
            'period': period,
            'source': models.GA,
            'full': full,
            'abstract': abstract,
            'digest': digest,
            'pdf': pdf
        })

        if isinstance(citations, int):
            citations = [citations]

        citations = list(zip(citations, [models.CROSSREF, models.SCOPUS, models.PUBMED]))
        # ll: [(1, 'crossref')]
        # ll: [(1, 'crossref'), (1, 'scopus')]
        # ll: [(1, 'crossref'), (1, 'scopus'), (1, 'pubmed')]
        citation_objs = []
        for citation_count, source in citations:
            citation_objs.append(logic.insert_citation({
                'doi': utils.msid2doi(msid),
                'source': source,
                'num': citation_count,
                'source_id': 'asdf'
            }))
        return metric, citation_objs

    # abbr_list has to be a list of [(msid, (citations, pdf, full)), ...]
    if isinstance(abbr_list, dict):
        abbr_list = abbr_list.items()

    date = BASE_DATE - timedelta(days=len(abbr_list))
    for msid, data in abbr_list:
        date += timedelta(days=1)
        wrangle(msid, data, date)

#
# tests the insert_logic above
#

@pytest.mark.django_db
def test_insert_metrics():
    cases = {
        # msid, citations, downloads, views
        '1234': (1, 2, 3),
        '5677': (4, 6, 7)
    }
    insert_metrics(cases)
    assert models.Article.objects.count() == len(cases.keys())
    assert models.Metric.objects.count() == len(cases.keys())
    assert models.Citation.objects.count() == len(cases.keys())

    for msid, triple in cases.items():
        doi = utils.msid2doi(msid)
        models.Article.objects.get(doi=doi)

        citations, downloads, views = triple

        models.Metric.objects.get(article__doi=doi, pdf=downloads, full=views)
        models.Citation.objects.get(article__doi=doi, num=citations)

@pytest.mark.django_db
def test_insert_metrics_many_citations():
    cases = {
        # msid, citations, downloads, views
        '1234': ([1, 2, 3], 0, 0),
        '5678': ([4, 5, 6], 0, 0),
    }
    insert_metrics(cases)
    assert models.Article.objects.count() == len(cases.keys())
    assert models.Metric.objects.count() == len(cases.keys())

    assert models.Citation.objects.count() == len(cases.keys()) * 3
