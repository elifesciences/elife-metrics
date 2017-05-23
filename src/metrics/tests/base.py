import StringIO
import os, json
from django.test import TestCase as DjangoTestCase, TransactionTestCase
from django.core.management import call_command as call_dj_command
import unittest
from metrics import utils, models, logic
from datetime import timedelta, datetime

BASE_DATE = datetime(year=2001, month=1, day=1)

def resp_json(resp):
    # json.loads(resp.bytes.decode('utf-8')) # python3
    return json.loads(resp.content.decode('utf-8')) # resp.json() fails with header issues

def insert_metrics(abbr_list):
    "function to bypass scraping logic and insert metrics and citations directly into db"
    def wrangle(msid, data, date):
        full = abstract = digest = pdf = 0
        citations = [0]
        period = models.DAY
        source = models.GA

        if len(data) == 3:
            citations, pdf, full = data
        elif len(data) == 4:
            citations, pdf, full, period = data
        elif len(data) == 5:
            citations, pdf, full, period, source = data
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
            'source': source,
            'full': full,
            'abstract': abstract,
            'digest': digest,
            'pdf': pdf
        })

        if isinstance(citations, int):
            citations = [citations]

        citations = zip(citations, [models.CROSSREF, models.SCOPUS, models.PUBMED])
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

def call_command(*args, **kwargs):
    stdout = StringIO.StringIO()
    try:
        kwargs['stdout'] = stdout
        call_dj_command(*args, **kwargs)
    except SystemExit as err:
        return err.code, stdout.getvalue()
    raise AssertionError("command should *always* throw a systemexit()")

#
#
#

class SimpleBaseCase(unittest.TestCase):
    "use this base if you don't need database wrangling"
    table_id = 'ga:82618489'
    maxDiff = None
    this_dir = os.path.dirname(os.path.realpath(__file__))
    fixture_dir = os.path.join(this_dir, 'fixtures')

class BaseCase(SimpleBaseCase, DjangoTestCase):
    # https://docs.djangoproject.com/en/1.10/topics/testing/tools/#django.test.TestCase
    pass

class TransactionBaseCase(SimpleBaseCase, TransactionTestCase):
    pass

#
#
#

class BaseLogic(BaseCase):
    def test_insert_metrics(self):
        cases = {
            # msid, citations, downloads, views
            '1234': (1, 2, 3),
            '5677': (4, 6, 7)
        }
        insert_metrics(cases)
        self.assertEqual(models.Article.objects.count(), len(cases.keys()))
        self.assertEqual(models.Metric.objects.count(), len(cases.keys()))
        self.assertEqual(models.Citation.objects.count(), len(cases.keys()))

        for msid, triple in cases.items():
            doi = utils.msid2doi(msid)
            models.Article.objects.get(doi=doi)

            citations, downloads, views = triple

            models.Metric.objects.get(article__doi=doi, pdf=downloads, full=views)
            models.Citation.objects.get(article__doi=doi, num=citations)

    def test_insert_metrics_many_citations(self):
        cases = {
            # msid, citations, downloads, views
            '1234': ([1, 2, 3], 0, 0),
            '5678': ([4, 5, 6], 0, 0),
        }
        insert_metrics(cases)
        self.assertEqual(models.Article.objects.count(), len(cases.keys()))
        self.assertEqual(models.Metric.objects.count(), len(cases.keys()))

        self.assertEqual(models.Citation.objects.count(), len(cases.keys()) * 3)
