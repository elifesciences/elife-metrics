__description__ = """Bulk loading of eLife metrics from Google Analytics."""

import os
from . import core
from . import utils
from article_metrics.utils import lmap, lfilter
from .core import ymd
from datetime import datetime, timedelta
import logging
from collections import OrderedDict

LOG = logging.getLogger(__name__)

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
