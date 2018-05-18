from django.core.management.base import BaseCommand
from article_metrics.pm import bulkload_pmids

import logging
LOG = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'imports all metrics from google analytics'

    def add_arguments(self, parser):
        parser.add_argument('path')

    def handle(self, *args, **options):
        path = options['path']
        print((bulkload_pmids.load_csv(path)))
