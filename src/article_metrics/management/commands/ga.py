import sys
import pprint
from django.core.management.base import BaseCommand
from django.conf import settings
from article_metrics import ga_metrics
from article_metrics.ga_metrics import utils

import logging
LOG = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'replacements for elife-ga-metrics "regenerate" and "run" bash scripts'

    def add_arguments(self, parser):
        parser.add_argument('--action', choices=['run', 'run-bulk', 'regenerate', 'regenerate-2016'])

    def handle(self, *args, **options):
        key = options['action']
        actions = {
            'run': ga_metrics.core.main,
            'run-bulk': ga_metrics.bulk.article_metrics, # the 'main' essentially
            'regenerate': ga_metrics.bulk.regenerate_results,
            'regenerate-2016': ga_metrics.bulk.regenerate_results_2016,
        }
        result = actions[key](utils.norm_table_id(settings.GA_TABLE_ID))
        self.stdout.write(pprint.pformat(result))
        self.stdout.flush()
        sys.exit(0)
