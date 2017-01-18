__description__ = "General purpose interesting metrics we can pull from GA"

import sys
import utils, core
from .utils import ymd
from collections import OrderedDict
from datetime import datetime

#
# queries
#

def total_traffic_monthly_query(table_id, from_date=None, to_date=None):
    "returns "
    from_date = from_date or core.VIEWS_INCEPTION
    to_date = to_date or datetime.now()
    month_range = utils.dt_month_range(from_date, to_date)
    from_date, to_date = month_range[0][0], month_range[-1][1]
    return {
        'ids': table_id,
        'max_results': 10000, # 10,000 is the max GA will ever return
        'start_date': ymd(from_date),
        'end_date': ymd(to_date),
        'metrics': 'ga:pageviews',
        'dimensions': 'ga:year,ga:month'
    }


#
# interfaces
#

def total_traffic_monthly(table_id, from_date=None, to_date=None):
    results = core.query_ga(total_traffic_monthly_query(table_id, from_date, to_date))
    rows = OrderedDict(map(lambda r: ("%s-%s" % (r[0], r[1]), int(r[2])), results['rows']))
    average = 0
    if rows:
        average = sum(rows.values()) / len(rows)
    return {
        'results': rows,
        'average': average,
        'from_date': results['query']['start-date'],
        'to_date': results['query']['end-date']
    }


#####

def main(args):
    pass

if __name__ == '__main__':
    main(sys.argv[1:])
