import json
from . import base
from django.core.management import CommandError

class One(base.BaseCase):
    def test_tasks_cmd(self):
        "an dry ingest can be passed without error"
        self.assertRaises(CommandError, base.call_command, 'tasks') # a task is required
        self.assertRaises(CommandError, base.call_command, 'tasks', 'footask') # an actual task is required

    def test_tasks_actual_cmd(self):
        errcode, stdout = base.call_command('tasks', 'routing-table')
        self.assertEqual(errcode, 0) # no problems
        self.assertTrue(json.loads(stdout)) # we don't care what the output is, so long as it's json
