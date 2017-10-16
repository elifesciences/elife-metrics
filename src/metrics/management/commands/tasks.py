import json
from django.conf import settings
from django.core.management.base import BaseCommand
from metrics import load_routing

import logging
LOG = logging.getLogger('debugger')

def print_journal_routes():
    "converts the journal routes into GA queries"
    print json.dumps(load_routing.load(settings.JOURNAL_ROUTES), indent=4)

def load_journal_routes():
    "load the journal routes from the schema directory and create Page objects"
    load_routing.insert_all(load_routing.load(settings.JOURNAL_ROUTES))

def update_page_metrics():
    "query GA for page view counts for all known pages"
    load_routing.update_all_page_counts()

TASKS = {
    'journal-routes': print_journal_routes,
    'load-journal-routes': load_journal_routes,
    'update-page-metrics': update_page_metrics
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
