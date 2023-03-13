import os
from django.test import TestCase as DjangoTestCase
from metrics import models
from article_metrics.utils import lmap

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIR = os.path.join(THIS_DIR, 'fixtures')

def fixture_path(path):
    path = os.path.join(THIS_DIR, 'fixtures', path)
    assert os.path.exists(path), "fixture not found: %s" % path
    return path

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
    this_dir = THIS_DIR
    fixture_dir = FIXTURE_DIR
