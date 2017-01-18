from django.db import models

class Article(models.Model):
    doi = models.CharField(max_length=255, help_text="article identifier")

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
    "daily article metrics as reported by Google Analytics"
    article = models.ForeignKey(Article)
    date = models.CharField(max_length=10, blank=True, null=True, help_text="the date this metric is for in YYYY-MM-DD, YYYY-MM and YYYY formats or None for 'all time'")
    period = models.CharField(max_length=10, choices=metric_period_list())
    source = models.CharField(max_length=2, choices=metric_source_list())

    full = models.PositiveIntegerField(help_text="article page views")
    abstract = models.PositiveIntegerField(help_text="article abstract page views")
    digest = models.PositiveIntegerField(help_text="article digest page views")
    pdf = models.PositiveIntegerField(help_text="pdf downloads")

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
