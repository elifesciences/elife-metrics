from collections import OrderedDict
import csv
from django.core.management.base import BaseCommand
from metrics import api_v2_logic as logic, models, utils

import logging
LOG = logging.getLogger(__name__)

def hw_terminator_report():
    with open('hw-term-report.csv', 'w') as fh:
        writer = None

        for art in models.Article.objects.all():
            try:
                msid = utils.doi2msid(art.doi)
                ga_stats = logic.article_stats(**{
                    'msid': msid,
                    'period': models.DAY,
                    'source': models.GA,
                    'prefer_hw_metrics': False,
                })
                hw_stats = logic.article_stats(**{
                    'msid': msid,
                    'period': models.DAY,
                    'source': models.HW,
                    'prefer_hw_metrics': False,
                })
                comb_stats = logic.article_stats(**{
                    'msid': msid,
                    'period': models.DAY,
                    'source': None,
                    'prefer_hw_metrics': True,
                })
                terminator = logic.hw_terminator(msid, models.DAY)

                ga_before, ga_after = logic.gabeforeafter(msid, models.DAY, terminator)

                row = OrderedDict([
                    ('msid', msid),
                    ('hw-term', terminator),

                    ('total_ga_views', ga_stats[0]),
                    ('total_ga_dls', ga_stats[1]),

                    ('before_ga_views', ga_before['views']),
                    ('before_ga_dls', ga_before['dls']),

                    ('total_hw_views', hw_stats[0]),
                    ('total_hw_dls', hw_stats[1]),

                    ('after_ga_views', ga_after['views']),
                    ('after_ga_dls', ga_after['dls']),

                    ('comb_views', comb_stats[0]),
                    ('comb_dls', comb_stats[1]),

                ])

                if not writer:
                    writer = csv.DictWriter(fh, fieldnames=row.keys())
                    writer.writeheader()

                writer.writerow(row)
            except BaseException as err:
                LOG.exception("unhandled exception for article %r: %s", art, err)
                continue


class Command(BaseCommand):
    help = 'imports all metrics from google analytics'

    def add_arguments(self, parser):
        parser.add_argument('cmd')

    def handle(self, *args, **options):
        cmd = options['cmd']

        known_cmds = {
            'hw-term-rep': hw_terminator_report,
        }

        try:
            fn = known_cmds[cmd]
            fn()
            exit(0)
        except KeyError:
            print 'unknown command %r' % cmd

        exit(1)
