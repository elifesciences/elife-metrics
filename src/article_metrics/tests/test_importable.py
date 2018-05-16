from datetime import datetime
from metrics import logic
from .base import BaseCase
#import os
#from os.path import join

class TestAllImportable(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_fixtures_importable(self):
        """all fixtures in the fixtures/importable directory can be
        imported. just drop the fixture into the directory and this
        case will pick it up and import it."""
        #path = join(self.fixture_dir, 'importable')
        #file_list = os.listdir(path)
        #path_list = map(lambda fname: join(path, fname), file_list)

        from_dt = datetime(year=2016, month=2, day=1)
        to_dt = datetime(year=2016, month=2, day=29)
        logic.import_ga_metrics('monthly', from_date=from_dt, to_date=to_dt)
        logic.import_ga_metrics('monthly', from_date=from_dt, to_date=to_dt)

        # for path in path_list:
        #    logic.import
        #    self.assertTrue(False)
