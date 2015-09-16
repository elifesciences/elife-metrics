from collections import OrderedDict
from django.test import TestCase, Client
from django.core.urlresolvers import reverse
from metrics import models, logic
from datetime import datetime

class BaseCase(TestCase):
    def __init__(self, *args, **kwargs):
        super(BaseCase, self).__init__(*args, **kwargs)
        self.maxDiff = None


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


class TestAPI(BaseCase):
    def setUp(self):
        self.c = Client()

    def tearDown(self):
        pass

    def test_asdfasdf(self):
        "a very simple set of data returns the expected daily and monthly data in the expected structure"
        day_to_import = datetime(year=2015, month=9, day=11)
        logic.import_ga_metrics(from_date=day_to_import, to_date=day_to_import)
        doi = '10.7554/eLife.09560'
        expected_data = {
            doi: {
                'daily': OrderedDict({
                    '2015-09-11': OrderedDict({
                        'full': 21922,
                        'abstract': 325,
                        'digest': 114,
                        'pdf': 1533,
                    }),
                    #2015-09-12: {
                    #    ....
                    #
                    #}
                }),
                'monthly': {},
                #    '2015-09': {
                #        'full': 21922,
                #        'abstract': 325,
                #        'digest': 114,
                #        'pdf': 1533,
                #    },
                #},
                #'total': {
                #    '2015-09-11': {
                #        'full': ....,
                #        'abstract': ...,
                #        'digest': ...,
                #    },
                #},
            },
        }
        url = reverse('api-article-metrics', kwargs={'doi': doi})
        print url
        resp = self.c.get(url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(expected_data, resp.data)

        
