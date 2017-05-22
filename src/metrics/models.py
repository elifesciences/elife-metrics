from django.db import models
from django.db.models import DateTimeField, PositiveIntegerField, ForeignKey, CharField
from django.conf import settings
from django.core.exceptions import ValidationError

from django.dispatch import receiver
from django.db.models.signals import pre_save

@receiver(pre_save)
def pre_save_handler(sender, instance, *args, **kwargs):
    # validate everything before save.
    instance.full_clean()

def validate_doi(val):
    "validates given value is not just any doi, but a known doi"
    known_doi_prefix_list = [settings.DOI_PREFIX]
    for prefix in known_doi_prefix_list:
        if str(val).startswith(prefix):
            return
    raise ValidationError('%r has an unknown doi prefix. known prefixes: %r' % (val, known_doi_prefix_list))

class Article(models.Model):
    doi = CharField(max_length=255, unique=True, help_text="article identifier", validators=[validate_doi])
    pmid = PositiveIntegerField(unique=True, blank=True, null=True)
    pmcid = CharField(max_length=10, unique=True, blank=True, null=True)

    class Meta:
        ordering = ('-doi',)

    def __unicode__(self):
        return self.doi

    def __repr__(self):
        return '<Article %r>' % self.doi

DAY, MONTH, EVER = 'day', 'month', 'ever'

def metric_period_list():
    return [
        (DAY, 'Daily'),
        (MONTH, 'Monthly'),
        #('year', 'Yearly'),
        (EVER, 'All time'),
    ]

KNOWN_METRIC_SOURCES = GA, HW = 'ga', 'hw'
KNOWN_METRIC_SOURCE_LABELS = GA_LABEL, HW_LABEL = 'Google Analytics', 'HighWire'

def metric_source_list():
    return [
        (GA, GA_LABEL),
        (HW, HW_LABEL),
    ]

class Metric(models.Model):
    article = ForeignKey(Article)
    date = CharField(max_length=10, blank=True, null=True, help_text="the date this metric is for in YYYY-MM-DD, YYYY-MM and YYYY formats or None for 'all time'")
    period = CharField(max_length=10, choices=metric_period_list())
    source = CharField(max_length=2, choices=metric_source_list())

    full = PositiveIntegerField(help_text="article page views")
    abstract = PositiveIntegerField(help_text="article abstract page views")
    digest = PositiveIntegerField(help_text="article digest page views")
    pdf = PositiveIntegerField(help_text="pdf downloads")

    datetime_record_created = DateTimeField(auto_now_add=True)
    datetime_record_updated = DateTimeField(auto_now=True)

    @property
    def downloads(self):
        return self.pdf

    @property
    def views(self):
        return self.abstract + self.full + self.digest

    def source_label(self):
        return 'highwire' if self.source == HW else 'ga'

    class Meta:
        unique_together = ('article', 'date', 'period', 'source')
        ordering = ('date',)

    def as_row(self):
        return {
            'full': self.full,
            'abstract': self.abstract,
            'digest': self.digest,
            'pdf': self.pdf,
            'source': self.source,
            'period': self.period,
            'date': self.date,
        }

    def __unicode__(self):
        return '%s,%s,%s,%s,%s,%s' % (self.article, self.date, self.source, self.full, self.pdf, self.digest)

    def __repr__(self):
        return u'<Metric %s>' % self.__unicode__()

#
#
#

SOURCES = CROSSREF, PUBMED, SCOPUS = 'crossref', 'pubmed', 'scopus'
SOURCE_LABELS = CROSSREF_LABEL, PUBMED_LABEL, SCOPUS_LABEL = 'Crossref', 'PubMed Central', 'Scopus'

SOURCE_CHOICES = zip(SOURCES, SOURCE_LABELS)
SOURCE_CHOICES_IDX = dict(SOURCE_CHOICES)

class CitationManager(models.Manager):
    def get_queryset(self):
        "always join with the article table"
        return super(CitationManager, self).get_queryset().select_related('article')

class Citation(models.Model):
    article = ForeignKey(Article)
    num = PositiveIntegerField()
    source = CharField(max_length=10, choices=SOURCE_CHOICES) # scopus, crossref, pubmed, etc
    source_id = CharField(max_length=255) # a link back to this article for given source

    datetime_record_created = DateTimeField(auto_now_add=True)
    datetime_record_updated = DateTimeField(auto_now=True)

    objects = CitationManager()

    def source_label(self):
        return SOURCE_CHOICES_IDX.get(self.source)

    class Meta:
        # an article may only have one instance of a source
        unique_together = ('article', 'source')
        ordering = ('-num',)

    def __unicode__(self):
        # ll: 10.7554/eLife.09560,crossref,33
        return '%s,%s,%s' % (self.article, self.source, self.num)

    def __repr__(self):
        return '<Citation %s>' % self
