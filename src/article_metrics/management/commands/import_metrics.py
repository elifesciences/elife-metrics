import time, math
from collections import OrderedDict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from article_metrics import logic, models
import metrics
import logging

DEBUG_LOG = logging.getLogger('debugger')
LOG = logging.getLogger(__name__)

def timeit(label):
    def wrap1(fn):
        def wrap2(*args, **kwargs):
            start = time.time()
            LOG.info("timing for import_metrics %r started" % label)
            try:
                retval = fn(*args, **kwargs)
            except BaseException as be:
                end = time.time()
                diff_secs = round(end - start, 2)
                # "timing for import_metrics 'crossref-citations' (failed, KeyboardInterrupt): 58 seconds"
                LOG.info("timing for import_metrics %r (failed, %s): %d seconds" % (label, type(be).__name__, diff_secs))
                raise be
            end = time.time()
            diff_secs = round(end - start, 2)
            # "timing for import_metrics 'crossref-citations': 58 seconds"
            LOG.info("timing for import_metrics %r: %d seconds" % (label, diff_secs))
            return retval
        return wrap2
    return wrap1

class Command(BaseCommand):
    help = 'imports all metrics from google analytics'

    def add_arguments(self, parser):
        # views+downloads
        # import the last two days by default
        # lsh@2023-08-14: changed default from 2 days to 5 days.
        # as results from the last 3 days are no longer cached because of partial results,
        # this will see 2 cache hits and 3 cache misses on days with partial results.
        parser.add_argument('--days', nargs='?', type=int, default=5)
        # import the last two months by default
        parser.add_argument('--months', nargs='?', type=int, default=2)

        # use cache files if they exist
        parser.add_argument('--cached', dest='cached', action="store_true", default=True)
        # import *only* from cached results, don't try to fetch from remote
        parser.add_argument('--only-cached', dest='only_cached', action="store_true", default=False)

    @timeit("overall")
    def handle(self, *args, **options):
        today = datetime.now()
        n_days_ago = today - timedelta(days=options['days'])
        n_months_ago = today - relativedelta(months=options['months'])
        use_cached = options['cached']
        use_only_cached = options['only_cached']

        from_date = n_days_ago
        to_date = today

        GA_DAILY, GA_MONTHLY = 'ga-daily', 'ga-monthly'
        NA_METRICS = 'non-article-metrics'

        # the mapping of sources and how to call them.
        # date ranges and caching arguments don't matter to citations right now
        # caching is feasible, but only crossref supports querying citations by date range
        sources = OrderedDict([
            # lsh@2023-08-14: `logic.update_all_ptypes_latest_frame` queries on frame boundaries.
            # Because the frame boundary extends to 'today' a cache file will not be generated.
            # This is what we want. For now it avoids accumulating files and partial results at the
            # expense of daily queries with larger results (<10MB).
            (NA_METRICS, (timeit("non-article-metrics")(metrics.logic.update_all_ptypes_latest_frame),)),
            (GA_DAILY, (timeit("article-metrics-daily")(logic.import_ga_metrics), 'daily', from_date, to_date, use_cached, use_only_cached)),
            (GA_MONTHLY, (timeit("article-metrics-monthly")(logic.import_ga_metrics), 'monthly', n_months_ago, to_date, use_cached, use_only_cached)),
            (models.CROSSREF, (timeit("crossref-citations")(logic.import_crossref_citations),)),
            (models.SCOPUS, (timeit("scopus-citations")(logic.import_scopus_citations),)),
            (models.PUBMED, (timeit("pmc-citations")(logic.import_pmc_citations),)),
        ])

        try:
            start_time = time.time() # seconds since epoch
            for source, row in sources.items():
                try:
                    fn, args = row[0], row[1:]
                    fn(*args)
                except KeyboardInterrupt:
                    print('ctrl-c caught, skipping rest of %s' % source)
                    print('use ctrl-c again to abort immediately')
                    time.sleep(1)

                except BaseException as err:
                    DEBUG_LOG.exception("unhandled error in source %s: %s", source, err)
                    continue

            end_time = time.time()

            elapsed_seconds = end_time - start_time
            elapsed_hours = math.ceil(elapsed_seconds / 3600)
            timeit("notifications")(logic.recently_updated_article_notifications)(hours=elapsed_hours)

        except KeyboardInterrupt:
            print('caught second ctrl-c')
            print('quitting')
            exit(1)

        except BaseException:
            msg = "unhandled exception calling the import-metrics command."
            DEBUG_LOG.exception(msg) # capture a stacktrace
            DEBUG_LOG.critical(msg) # we can't recover, this command must exit
            exit(1)

        self.stdout.write("...done\n")
        self.stdout.flush()
