import json
from django.conf import settings
from django.core.management.base import BaseCommand
from metrics import load_routing

import logging
LOG = logging.getLogger('debugger')

def print_journal_routes(stdout):
    "converts the journal routes into GA queries"
    stdout.write(json.dumps(load_routing.load_journal_route_file(settings.JOURNAL_ROUTES), indent=4))

def print_journal_redirects(stdout):
    stdout.write(json.dumps(load_routing.load_nginx_redirect_file(settings.JOURNAL_REDIRECTS), indent=4))

def load_journal_routes(stdout):
    "load the journal routes from the schema directory and create Page objects"
    load_routing.insert_all(load_routing.load(settings.JOURNAL_ROUTES))

#def missing_routes(stdout):
#    stdout.write(json.dumps(load_routing.old_paths_without_a_new_route()))

def write_final_routes(stdout):
    stdout.write(json.dumps(load_routing.dump_routing_table(), indent=4))

def print_final_routes(stdout):
    stdout.write(json.dumps(load_routing.routing_table(), indent=4))

TASKS = {
    'journal-routes': print_journal_routes,
    'journal-redirects': print_journal_redirects,
    'load-journal-routes': load_journal_routes,
    #'missing-routes': missing_routes,
    'final-routes': print_final_routes,
    'write-final-routes': write_final_routes,
}

class Command(BaseCommand):
    help = 'imports all metrics from google analytics'

    def add_arguments(self, parser):
        parser.add_argument('task', choices=TASKS.keys())

    def handle(self, *args, **options):
        try:
            TASKS[options['task']](self.stdout)

        except KeyboardInterrupt:
            exit(1)

        except BaseException as err:
            LOG.exception("unhandled exception executing task: %s", err)
            exit(1)

        finally:
            self.stdout.flush()

        exit(0)
