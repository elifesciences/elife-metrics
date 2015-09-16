from datetime import datetime, timedelta
import elife_ga_metrics as ga_metrics
from elife_ga_metrics import bulk
from django.conf import settings
import models
from django.db import transaction

def subdict(d, kl):
    return {k:v for k, v in d.items() if k in kl}

def create_row(doi, ymd, views, downloads):
    "creates a row from the given data suitable for inserting into the metrics table"
    if not views:
        views = {
            'full': 0,
            'abstract': 0,
            'digest': 0
        }
    views['pdf'] = downloads or 0

    row = {
        'date': ymd,
        'type': 'day'
    }
    row.update(views)
    return row

@transaction.atomic
def import_ga_metrics(from_date=None, to_date=None):
    table_id = 'ga:%s' % settings.GA_TABLE_ID
    the_beginning = ga_metrics.core.VIEWS_INCEPTION
    yesterday = datetime.now() - timedelta(days=1)

    if not from_date:
        from_date = the_beginning

    if not to_date:
        to_date = yesterday
    
    # don't import today's partial results. they're available but lets wait until tomorrow
    results = bulk.daily_metrics_between(table_id, from_date, to_date)
    for ymd, metrics in results.items():
        print 'processing',ymd
        
        downloads = metrics['downloads']
        views = metrics['views']
        
        doi_list = set(views.keys()).union(downloads.keys())
        for doi in doi_list:
            row = create_row(doi, ymd, views.get(doi), downloads.get(doi))
            article_obj, created = models.Article.objects.get_or_create(doi=doi)
            row['article'] = article_obj
            sd = subdict(row, ['article', 'date', 'type'])
            try:
                models.GAMetric.objects.get(**sd)
                #print 'metric found for %r, skipping' % sd
                # update here if necessary
            except models.GAMetric.DoesNotExist:
                obj = models.GAMetric(**row)
                obj.save()
                #print 'saved',obj
