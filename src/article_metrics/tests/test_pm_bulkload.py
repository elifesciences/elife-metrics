from django.conf import settings
from metrics.pm import bulkload_pmids
from . import base
from metrics import models
from os.path import join

class Load(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_load(self):
        self.assertEqual(0, models.Article.objects.count())
        fixture = join(self.fixture_dir, 'pm-fixture.csv')
        bulkload_pmids.load_csv(fixture)
        self.assertEqual(9, models.Article.objects.count())
        for art in models.Article.objects.all():
            self.assertTrue(art.pmid)
            self.assertTrue(art.pmcid)
            self.assertTrue(art.doi)
            self.assertTrue(art.doi.startswith('10.7554/eLife.'))

    def test_load_missing(self):
        "missing values in csv don't prevent load"
        self.assertEqual(0, models.Article.objects.count())
        doi = settings.DOI_PREFIX + '/eLife.123456'
        pmcid = '7890123'
        row = {
            'DOI': doi,
            'PMCID': pmcid,
            'PMID': ''
        }
        bulkload_pmids.update_article(row)
        self.assertEqual(1, models.Article.objects.count())
        art = models.Article.objects.get(doi=doi)
        self.assertEqual(art.pmid, None)
        self.assertEqual(art.pmcid, pmcid)
