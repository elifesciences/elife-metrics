import os
from django.test import TestCase as DjangoTestCase
import unittest
from metrics import utils, models, logic

def insert_metrics(abbr_map):
    def wrangle(msid, data):
        citations = full = abstract = digest = pdf = 0
        if len(data) == 3:
            citations, pdf, full = data
        else:
            raise ValueError("cannot handle row of length %s" % len(data))
        metric = logic.insert_row({
            'doi': utils.msid2doi(msid),
            'date': '2017-01-01',
            'period': models.DAY,
            'source': models.GA,
            'full': full,
            'abstract': abstract,
            'digest': digest,
            'pdf': pdf
        })
        citation = logic.insert_citation({
            'doi': utils.msid2doi(msid),
            'source': models.CROSSREF,
            'num': citations,
            'source_id': 'asdf'
        })
        return metric, citation
    return [wrangle(msid, data) for msid, data in abbr_map.items()]

class SimpleBaseCase(unittest.TestCase):
    "use this base if you don't need database wrangling"
    table_id = 'ga:82618489'
    maxDiff = None
    this_dir = os.path.dirname(os.path.realpath(__file__))
    fixture_dir = os.path.join(this_dir, 'fixtures')

class BaseCase(SimpleBaseCase, DjangoTestCase):
    # https://docs.djangoproject.com/en/1.10/topics/testing/tools/#django.test.TestCase
    pass


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
