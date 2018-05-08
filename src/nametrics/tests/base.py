import os
from django.test import TestCase as DjangoTestCase

class BaseCase(DjangoTestCase):
    maxDiff = None
    this_dir = os.path.dirname(os.path.realpath(__file__))
    fixture_dir = os.path.join(this_dir, 'fixtures')
