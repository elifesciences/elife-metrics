from django.urls import reverse
from django.test import Client

def test_index():
    url = reverse('index')
    resp = Client().get(url)
    assert resp.status_code == 200
