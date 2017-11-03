from django.core.management.base import BaseCommand
from metrics import load_routing as lr
from metrics.utils import lossy_json_dumps

import logging
LOG = logging.getLogger('debugger')

def print_routes(stdout):
    stdout.write(lossy_json_dumps(lr.routing_table(), indent=4))

TASKS = {
    'routing-table': print_routes,
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
