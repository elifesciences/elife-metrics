import os
from django.test import TestCase as DjangoTestCase

class SimpleBaseCase(unittest.TestCase):
    "use this base if you don't need database wrangling"
    table_id = 'ga:82618489'
    maxDiff = None
    this_dir = os.path.dirname(os.path.realpath(__file__))
    fixture_dir = os.path.join(this_dir, 'fixtures')

class BaseCase(SimpleBaseCase, DjangoTestCase):
    pass
