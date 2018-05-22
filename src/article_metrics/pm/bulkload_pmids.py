"""PMC provide a CSV of it's DB via FTP."""
from article_metrics import models, utils
from article_metrics.utils import create_or_update, lmap, ensure
from django.conf import settings
from django.db import transaction
import csv
import logging

LOG = logging.getLogger(__name__)

def update_article(row):
    data = {
        'doi': row['DOI'],
        'pmcid': row['PMCID'],
        'pmid': row['PMID'] or None,
    }
    ensure(data['doi'].startswith(settings.DOI_PREFIX), "refusing to create/update non-journal article: %s" % row)
    if not data['pmid']:
        LOG.warn("no pmid for %s" % data['doi'])

    # the doi values in the csv data look perfect and I've never had a problem with them
    # however
    # we only do it once per new production machine and it doesn't hurt to check
    utils.doi2msid(data['doi'], allow_subresource=False)

    return create_or_update(models.Article, data, ['doi'], create=True, update=True, update_check=True)

@transaction.atomic
def load_csv(path):
    with open(path, 'r') as fh:
        reader = csv.DictReader(fh)
        return lmap(update_article, reader)
