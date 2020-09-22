from . import base
from django.urls import reverse
from django.test import Client

class Views(base.BaseCase):
    def test_index(self):
        url = reverse('index')
        resp = Client().get(url)
        self.assertEqual(resp.status_code, 200)
