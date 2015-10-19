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
        # use cache files if they exist
        parser.add_argument('--cached', nargs='?', type=bool, default=True)
        # import *only* from cached results
        parser.add_argument('--only-cached', nargs='?', type=bool, default=False)
        # ignore settings for months?
        # caching works a little too well for months. not a problem unless you
        # want the value to be updated each day. month values are not derived from
        # day values so caching needs to be off.
        parser.add_argument('--ignore-caching-on-months', nargs='?', type=bool, default=False)

    def handle(self, *args, **options):
        today = datetime.now()
        n_days_ago = today - timedelta(days=options['days'])
        n_months_ago = today - relativedelta(months=options['months'])
        use_cached = options['cached']
        only_cached = options['only_cached']
        
        from_date = n_days_ago
        to_date = today
        
        LOG.info("importing daily stats")
        logic.import_ga_metrics('daily', from_date, to_date, use_cached, only_cached)
        logic.import_hw_metrics('daily', from_date, to_date)

        from_date = n_months_ago
        if options['ignore_caching_on_months']:
            use_cached = False

        LOG.info("import monthly stats")
        logic.import_ga_metrics('monthly', from_date, to_date, use_cached, only_cached)
        logic.import_hw_metrics('monthly', from_date, to_date)
        
        self.stdout.write("...done\n")
        self.stdout.flush()
