import argparse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand, CommandError
from metrics import logic

import logging
LOG = logging.getLogger(__name__)

def hw_or_ga(v):
    pv = v.lower().strip()
    if not pv in ['ga', 'hw']:
        raise argparse.ArgumentTypeError("'--just-source' accepts only 'hw' or 'ga'" % v)
    return pv

def first(x):
    try:
        return x[0]
    except KeyError:
        return None

def rest(x):
    return x[1:]

class Command(BaseCommand):
    help = 'imports all metrics from google analytics'

    def add_arguments(self, parser):
        # import the last two days by default
        parser.add_argument('--days', nargs='?', type=int, default=2)
        # import the last two months by default
        parser.add_argument('--months', nargs='?', type=int, default=2)
        
        # use cache files if they exist
        parser.add_argument('--cached', dest='cached', action="store_true", default=False)
        # import *only* from cached results
        parser.add_argument('--only-cached', dest='only_cached', action="store_true", default=False)

        parser.add_argument('--just-source', nargs='?', dest='just_source', type=hw_or_ga, default=None)
        
        # ignore settings for months?
        # caching works a little too well for months. not a problem unless you
        # want the value to be updated each day. month values are not derived from
        # day values so caching needs to be off.
        # UPDATE: problem is with argparse. this opt might not even be needed
        #parser.add_argument('--ignore-caching-on-months', nargs='?', type=bool, default=False)

    def handle(self, *args, **options):
        today = datetime.now()
        n_days_ago = today - timedelta(days=options['days'])
        n_months_ago = today - relativedelta(months=options['months'])
        use_cached = options['cached']
        only_cached = options['only_cached']
        
        from_date = n_days_ago
        to_date = today

        using_sources = ['hw', 'ga'] if not options['just_source'] else [options['just_source']]

        # goddamn argparse and it's braindead bool casting
        #print 'use cached? %r only cached? %r' % (use_cached, only_cached)

        sources = {
            'ga': (logic.import_ga_metrics, 'daily', from_date, to_date, use_cached, only_cached),
            'hw': (logic.import_hw_metrics, 'daily', from_date, to_date)
        }        
        LOG.info("importing daily stats for sources %s", ", ".join(using_sources))
        [apply(first(row), rest(row)) for source, row in sources.items() if source in using_sources]

        from_date = n_months_ago
        #if options['ignore_caching_on_months']:
        #    use_cached = False

        LOG.info("import monthly stats")
        sources = {
            'ga': (logic.import_ga_metrics, 'monthly', from_date, to_date, use_cached, only_cached),
            'hw': (logic.import_hw_metrics, 'monthly', from_date, to_date)
        }
        [apply(first(row), rest(row)) for source, row in sources.items() if source in using_sources]
        self.stdout.write("...done\n")
        self.stdout.flush()
