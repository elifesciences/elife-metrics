import json
from django.conf import settings
from django.core.management.base import BaseCommand
from metrics import load_routing

import logging
LOG = logging.getLogger('debugger')

def ga_journal_routes():
    "converts the journal routes into GA queries"
    print json.dumps(load_routing.load(settings.JOURNAL_ROUTES), indent=4)
    

TASKS = {
    'ga-journal-routes': ga_journal_routes
}

class Command(BaseCommand):
    help = 'imports all metrics from google analytics'

    def add_arguments(self, parser):
        parser.add_argument('task', choices=TASKS.keys())

    def handle(self, *args, **options):
        try:
            TASKS[options['task']]()
        except KeyboardInterrupt:
            print "caught"
            exit(1)
