from metrics.pm import bulkload_pmids
import base
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
