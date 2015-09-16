from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from metrics import logic

class Command(BaseCommand):
    help = 'imports all metrics from google analytics'

    def add_arguments(self, parser):
        #parser.add_argument('poll_id', nargs='+', type=int)
        pass

    def handle(self, *args, **options):
        #day_to_import = datetime(year=2015, month=9, day=11)
        logic.import_ga_metrics() #from_date=day_to_import, to_date=day_to_import)
        self.stdout.write("done")
