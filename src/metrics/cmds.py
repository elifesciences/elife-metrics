# django's management.command feature is troublesome to mock
# it also encourages code to grow way out in the sticks
# this module brings it all back locally
import os, json
from django.conf import settings
from datetime import date
from . import logic, models
from article_metrics import utils
import logging
from functools import partial

LOG = logging.getLogger(__name__)

def ingest_command(type_list, replace_cache_files=False):
    try:
        supported_types = [t for t in type_list if t in models.PAGE_TYPES] or models.PAGE_TYPES
        update_ptype = partial(logic.update_ptype, replace_cache_files=replace_cache_files)
        utils.lmap(update_ptype, supported_types)
    except BaseException as err:
        LOG.exception(str(err))

def update_test_fixtures():

    # ga-response-events-frame2.json
    start = date(year=2018, month=1, day=1)
    end = date(year=2018, month=1, day=31)
    frame_query_list = logic.build_ga_query(models.EVENT, start, end)
    frame, query = frame_query_list[0]
    response = logic.query_ga(models.EVENT, query)
    path = os.path.join(settings.SRC_DIR, "metrics/tests/fixtures/ga-response-events-frame2.json")
    json.dump(response, open(path, 'w'), indent=4)
    print("wrote", path)
