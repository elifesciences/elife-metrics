from django.db import models

class Article(models.Model):
    doi = models.CharField(max_length=255, unique=True, help_text="article identifier")
    pmid = models.PositiveIntegerField(unique=True, blank=True, null=True)
    pmcid = models.CharField(max_length=10, unique=True, blank=True, null=True)

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

    def __unicode__(self):
        return '%s,%s,%s,%s,%s,%s' % (self.article, self.date, self.source, self.full, self.pdf, self.digest)

    def __repr__(self):
        return u'<Metric %s>' % self.__unicode__()

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

class Citation(models.Model):
    article = models.ForeignKey(Article)
    num = models.PositiveIntegerField()
    source = models.CharField(max_length=10, choices=source_choices()) # scopus, crossref, pubmed, etc
    source_id = models.CharField(max_length=255) # a link back to this article for given source

    class Meta:
        # an article may only have one instance of a source
        unique_together = ('article', 'source')
        ordering = ('-num',)

    def __unicode__(self):
        # ll: 10.7554/eLife.09560,crossref,33
        return '%s,%s,%s' % (self.article, self.source, self.num)

    def __repr__(self):
        return '<Citation %s>' % self
