from . import base

class One(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_call_import_metrics(self):
        "code coverage boost, nothing more"
        err_code, stdout = base.call_command('import_metrics', dry_run=True)
        self.assertEqual(err_code, 0)
        self.assertEqual(stdout, "")
