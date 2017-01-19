from django.test import Client
import base
from django.core.urlresolvers import reverse

class ApiV2(base.BaseCase):
    def setUp(self):
        self.c = Client()

    def tearDown(self):
        pass

    def test_api(self):
        cases = {
            '1234': (1, 2, 3),
            '5677': (4, 6, 7)
        }
        metric_list = ['citations', 'downloads', 'page-views']
        for msid, expected in cases.items():
            # go through each metric type and request the value
            for metric_idx, expected_val in enumerate(expected):
                metric = metric_list[metric_idx]
                url = reverse('v2:metrics', kwargs={'type': 'article', 'id': msid, 'metric': metric})
                resp = self.c.get(url)
                actual_val = resp.data()
                self.assertEqual(actual_val, expected_val)
