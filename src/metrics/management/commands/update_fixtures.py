import sys
from django.core.management.base import BaseCommand
from metrics import cmds
import logging
LOG = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'downloads and updates the fixtures used in testing'

    def handle(self, *args, **options):
        try:
            cmds.update_test_fixtures()
        except BaseException:
            LOG.exception("uncaught exception calling command 'update_test_fixtures'")
            sys.exit(1)
