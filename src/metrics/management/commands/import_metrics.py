from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand, CommandError
from metrics import logic

import logging
LOG = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'imports all metrics from google analytics'

    def add_arguments(self, parser):
        # import the last two days by default
        parser.add_argument('--days', nargs='?', type=int, default=2)
        # import the last two months by default
        parser.add_argument('--months', nargs='?', type=int, default=2)

    def handle(self, *args, **options):
        today = datetime.now()
        n_days_ago = today - timedelta(days=options['days'])
        n_months_ago = today - relativedelta(months=options['months'])
        
        LOG.info("importing daily stats")
        logic.import_ga_metrics('daily', from_date=n_days_ago, to_date=today)

        LOG.info("import monthly stats")
        logic.import_ga_metrics('monthly', from_date=n_months_ago, to_date=today)
        
        self.stdout.write("...done\n")
        self.stdout.flush()
