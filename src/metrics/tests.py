from django.test import TestCase
from metrics import models, logic
from datetime import datetime

class BaseCase(TestCase):
    pass


class TestImport(BaseCase):
    def setUp(self):
        pass
    
    def tearDown(self):
        pass

    def test_import_ga_daily_stats(self):
        "ensure that a basic import of a day's worth of metrics happens correctly"
        self.assertEqual(0, models.Article.objects.count())
        day_to_import = datetime(year=2015, month=9, day=11)
        logic.import_ga_metrics(from_date=day_to_import, to_date=day_to_import)
        expected_article_count = 1090 # we know this day reveals this many articles
        self.assertEqual(expected_article_count, models.Article.objects.count())
