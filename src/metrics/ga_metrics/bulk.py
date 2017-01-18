__description__ = """Bulk loading of eLife metrics from Google Analytics."""

import os
import core
import utils
from .core import ymd
from datetime import datetime, timedelta
import logging
from collections import OrderedDict

logging.basicConfig()
LOG = logging.getLogger(__name__)
LOG.level = logging.INFO

#
# bulk requests to ga
#

def generate_queries(table_id, query_func_name, datetime_list, use_cached=False, use_only_cached=False):
    "returns a list of queries to be executed by google"
    assert isinstance(query_func_name, str), "query func name must be a string"
    query_list = []
    for start_date, end_date in datetime_list:
        module = core.module_picker(start_date, end_date)
        query_func = getattr(module, query_func_name)
        query_type = 'views' if query_func_name == 'path_counts_query' else 'downloads'

        output_path = core.output_path(query_type, start_date, end_date)
        LOG.debug("looking for metrics here: %s", output_path)
        if use_cached:
            if os.path.exists(output_path):
                LOG.debug("we have %r results for %r to %r already", query_type, ymd(start_date), ymd(end_date))
                continue
            else:
                LOG.info("no cache file for %r results for %r to %r", query_type, ymd(start_date), ymd(end_date))
        else:
            LOG.debug("couldn't find file %r", output_path)

        if use_only_cached:
            LOG.info("skipping google query, using only cache files")
            continue

        q = query_func(table_id, start_date, end_date)
        query_list.append(q)

    if use_only_cached:
        # code problem
        assert query_list == [], "use_only_cached==True but we're accumulating queries somehow"

    return query_list

def bulk_query(query_list):
    "executes a list of queries"
    return map(core.query_ga_write_results, query_list)

#
# daily metrics
#

def metrics_for_range(table_id, dt_range_list, use_cached=False, use_only_cached=False):
    # tell core to do it's data wrangling for us (using cached data)
    results = OrderedDict({})
    for from_date, to_date in dt_range_list:
        res = core.article_metrics(table_id, from_date, to_date, use_cached, use_only_cached)
        results[(ymd(from_date), ymd(to_date))] = res
    return results

def daily_metrics_between(table_id, from_date, to_date, use_cached=True, use_only_cached=False):
    "does a DAILY query between two dates, NOT a single query within a date range"
    date_list = utils.dt_range(from_date, to_date)
    query_list = []

    views_dt_range = filter(core.valid_view_dt_pair, date_list)
    query_list.extend(generate_queries(table_id,
                                       'path_counts_query',
                                       views_dt_range,
                                       use_cached, use_only_cached))

    pdf_dt_range = filter(core.valid_downloads_dt_pair, date_list)
    query_list.extend(generate_queries(table_id,
                                       'event_counts_query',
                                       pdf_dt_range,
                                       use_cached, use_only_cached))

    bulk_query(query_list)

    # everything should be cached by now
    use_cached = True # DELIBERATE here. the above
    return metrics_for_range(table_id, views_dt_range, use_cached, use_only_cached)

#
# monthly metrics
#

def monthly_metrics_between(table_id, from_date, to_date, use_cached=True, use_only_cached=False):
    date_list = utils.dt_month_range(from_date, to_date)
    views_dt_range = filter(core.valid_view_dt_pair, date_list)
    pdf_dt_range = filter(core.valid_downloads_dt_pair, date_list)

    query_list = []
    query_list.extend(generate_queries(table_id,
                                       'path_counts_query',
                                       views_dt_range,
                                       use_cached, use_only_cached))

    query_list.extend(generate_queries(table_id,
                                       'event_counts_query',
                                       pdf_dt_range,
                                       use_cached, use_only_cached))
    bulk_query(query_list)

    # everything should be cached by now
    use_cached = True # DELIBERATE
    return metrics_for_range(table_id, views_dt_range, use_cached, use_only_cached)

#
#
#

# TODO: good idea!
def fill_gaps():
    """goes through all files we have output and looks for 'gaps' and
    then creates a query that will fill it. NOT a replacement for
    regenerate_results """

def regenerate_results(table_id, from_date=core.VIEWS_INCEPTION):
    "this will perform all queries again, overwriting the results in `output`"
    today = datetime.now()
    use_cached, use_only_cached = False, False
    LOG.info("querying daily metrics ...")
    daily_metrics_between(table_id,
                          from_date,
                          today,
                          use_cached, use_only_cached)

    LOG.info("querying monthly metrics ...")
    monthly_metrics_between(table_id,
                            from_date,
                            today,
                            use_cached, use_only_cached)

def regenerate_results_2016(table_id):
    return regenerate_results(table_id, datetime(2016, 1, 1))

#
# bootstrap
#

def article_metrics(table_id):
    "returns daily results for the last week and monthly results for the current month"
    from_date = datetime.now() - timedelta(days=1)
    to_date = datetime.now()
    use_cached, use_only_cached = True, not core.oauth_secrets()

    return {'daily': dict(daily_metrics_between(table_id,
                                                from_date,
                                                to_date,
                                                use_cached, use_only_cached)),

            'monthly': dict(monthly_metrics_between(table_id,
                                                    to_date,
                                                    to_date,
                                                    use_cached, use_only_cached))}

'''
if __name__ == '__main__':
    "call this app like: GA_TABLE='ga:12345678' python bulk.py"
    assert 'GA_TABLE' in os.environ, "the environment variable 'GA_TABLE' not found. It looks like 'ga:12345678'"
    pprint(article_metrics(os.environ['GA_TABLE']))
'''
