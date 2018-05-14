import sys
from django.core.management.base import BaseCommand
#from django.conf import settings
from nametrics import cmds
import logging
LOG = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'imports all non-article metrics from google analytics'

    def add_arguments(self, parser):
        parser.add_argument('--type', nargs='+', dest='just_type', type=str, default=[])

    def handle(self, *args, **options):
        try:
            cmds.ingest_command(options['just_type'])
            sys.exit(0)
        except BaseException as err:
            LOG.error("uncaught exception calling command 'ingest': %s" % err, extra={'cli-args': options})
            sys.exit(1)
