import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from metrics import logic, models

import logging
LOG = logging.getLogger(__name__)

'''
def hw_or_ga(v):
    pv = v.lower().strip()
    if not pv in ['ga', 'hw']:
        raise argparse.ArgumentTypeError("'--just-source' accepts only 'hw' or 'ga'" % v)
    return pv
'''

def first(x):
    try:
        return x[0]
    except (TypeError, KeyError):
        return None

def rest(x):
    return x[1:]

class Command(BaseCommand):
    help = 'imports all metrics from google analytics'

    def add_arguments(self, parser):
        # all
        #parser.add_argument('--just-source', nargs='?', dest='just_source', type=hw_or_ga, default=None)

        # views+downloads
        # import the last two days by default
        parser.add_argument('--days', nargs='?', type=int, default=2)
        # import the last two months by default
        parser.add_argument('--months', nargs='?', type=int, default=2)

        # use cache files if they exist
        parser.add_argument('--cached', dest='cached', action="store_true", default=False)
        # import *only* from cached results, don't try to fetch from remote
        parser.add_argument('--only-cached', dest='only_cached', action="store_true", default=False)

        # citations
        # ...

    def handle(self, *args, **options):
        today = datetime.now()
        n_days_ago = today - timedelta(days=options['days'])
        n_months_ago = today - relativedelta(months=options['months'])
        use_cached = options['cached']
        only_cached = options['only_cached']

        from_date = n_days_ago
        to_date = today

        # print 'use cached? %r only cached? %r' % (use_cached, only_cached)

        GA_DAILY, GA_MONTHLY = 'ga-daily', 'ga-monthly'

        # this determines the order the sources will be called in
        using_sources = [
            # models.GA,
            GA_DAILY,
            GA_MONTHLY,
            models.CROSSREF,
            models.SCOPUS,
            models.PUBMED
        ]
        # ... I know. parallelization would be nice.

        # the mapping of sources and how to call them.
        # date ranges and caching arguments don't matter to citations right now
        # caching is feasible, but only crossref supports querying citations by date range
        sources = {
            GA_DAILY: (logic.import_ga_metrics, 'daily', from_date, to_date, use_cached, only_cached),
            GA_MONTHLY: (logic.import_ga_metrics, 'monthly', n_months_ago, to_date, use_cached, only_cached),
            models.CROSSREF: (logic.import_crossref_citations,),
            models.SCOPUS: (logic.import_scopus_citations,),
            models.PUBMED: (logic.import_pmc_citations,),
        }

        LOG.info("importing metrics for sources %s", ", ".join(using_sources))

        try:
            for source, row in sources.items():
                if source in using_sources:
                    try:
                        first(row)(*rest(row))
                    except KeyboardInterrupt:
                        print 'ctrl-c caught.'
                        print 'use ctrl-c again to abort immediately'
                        time.sleep(2)
        except KeyboardInterrupt:
            print 'caught second ctrl-c'
            print 'quitting'
            exit(1)

        self.stdout.write("...done\n")
        self.stdout.flush()
