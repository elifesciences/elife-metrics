import os
from django.test import TestCase as DjangoTestCase
from nametrics import models
from metrics.utils import lmap

def insert_metrics(list_of_rows):
    def _insert(row):
        pid, ptype, date, views = row
        ptype, _ = models.PageType.objects.get_or_create(name=ptype)
        page, _ = models.Page.objects.get_or_create(type=ptype, identifier=pid)
        pcount, _ = models.PageCount.objects.get_or_create(page=page, views=views, date=date)
        return (ptype, page, pcount)
    return lmap(_insert, list_of_rows)

class BaseCase(DjangoTestCase):
    maxDiff = None
    this_dir = os.path.dirname(os.path.realpath(__file__))
    fixture_dir = os.path.join(this_dir, 'fixtures')
