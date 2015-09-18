from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from metrics import logic

class Command(BaseCommand):
    help = 'imports all metrics from google analytics'

    def add_arguments(self, parser):
        #parser.add_argument('poll_id', nargs='+', type=int)
        pass

    def handle(self, *args, **options):
        logic.import_ga_metrics('daily')
        logic.import_ga_metrics('monthly')
        self.stdout.write("done")
