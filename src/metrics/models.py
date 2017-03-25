from django.db import models
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
    doi = models.CharField(max_length=255, unique=True, help_text="article identifier", validators=[validate_doi])
    pmid = models.PositiveIntegerField(unique=True, blank=True, null=True)
    pmcid = models.CharField(max_length=10, unique=True, blank=True, null=True)

    class Meta:
        ordering = ('-doi',)

    def __str__(self):
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

GA, HW = 'ga', 'hw'

def metric_source_list():
    return [
        (GA, 'Google Analytics'),
        (HW, 'Highwire'),
    ]

class Metric(models.Model):
    article = models.ForeignKey(Article)
    date = models.CharField(max_length=10, blank=True, null=True, help_text="the date this metric is for in YYYY-MM-DD, YYYY-MM and YYYY formats or None for 'all time'")
    period = models.CharField(max_length=10, choices=metric_period_list())
    source = models.CharField(max_length=2, choices=metric_source_list())

    full = models.PositiveIntegerField(help_text="article page views")
    abstract = models.PositiveIntegerField(help_text="article abstract page views")
    digest = models.PositiveIntegerField(help_text="article digest page views")
    pdf = models.PositiveIntegerField(help_text="pdf downloads")

    @property
    def downloads(self):
        return self.pdf

    @property
    def views(self):
        return self.abstract + self.full + self.digest

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

    def __str__(self):
        return '%s,%s,%s,%s,%s,%s' % (self.article, self.date, self.source, self.full, self.pdf, self.digest)

    def __repr__(self):
        return '<Metric %s>' % self

#
#
#

CROSSREF, PUBMED, SCOPUS = 'crossref', 'pubmed', 'scopus'

def source_choices():
    return [
        (SCOPUS, "Elsevier's Scopus"),
        (CROSSREF, 'Crossref'),
        (PUBMED, 'PubMed Central'),
    ]


class CitationManager(models.Manager):
    def get_queryset(self):
        "always join with the article table"
        return super(CitationManager, self).get_queryset().select_related('article')

class Citation(models.Model):
    article = models.ForeignKey(Article)
    num = models.PositiveIntegerField()
    source = models.CharField(max_length=10, choices=source_choices()) # scopus, crossref, pubmed, etc
    source_id = models.CharField(max_length=255) # a link back to this article for given source

    objects = CitationManager()

    class Meta:
        # an article may only have one instance of a source
        unique_together = ('article', 'source')
        ordering = ('-num',)

    def __str__(self):
        # ll: 10.7554/eLife.09560,crossref,33
        return '%s,%s,%s' % (self.article, self.source, self.num)

    def __repr__(self):
        return '<Citation %s>' % self
