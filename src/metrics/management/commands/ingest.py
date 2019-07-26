import sys
from django.core.management.base import BaseCommand
from metrics import cmds
import logging
LOG = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'imports all non-article metrics from google analytics'

    def add_arguments(self, parser):
        parser.add_argument('--type', nargs='+', dest='just_type', type=str, default=[])
        parser.add_argument('--replace-cache-files', dest='replace_cache_files', action='store_const', const=True, default=False)

    def handle(self, *args, **options):
        try:
            cmds.ingest_command(type_list=options['just_type'], replace_cache_files=options['replace_cache_files'])
        except BaseException as err:
            LOG.error("uncaught exception calling command 'ingest': %s" % err, extra={'cli-args': options})
            sys.exit(1)
