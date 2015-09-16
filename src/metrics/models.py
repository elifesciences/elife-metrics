from django.db import models

class Article(models.Model):
    doi = models.CharField(max_length=255, help_text="article identifier")

    def __unicode__(self):
        return self.doi

    def __repr__(self):
        return '<Article %r>' % self.doi

def metric_type_list():
    return [
        ('day', 'Daily'),
        ('month', 'Monthly'),
        ('year', 'Yearly'),
        ('ever', 'All time'),
    ]

class GAMetric(models.Model):
    "daily article metrics as reported by Google Analytics"
    article = models.ForeignKey(Article)
    date = models.CharField(max_length=10, blank=True, null=True, help_text="the date this metric is for in YYYY-MM-DD, YYYY-MM and YYYY formats or None for 'all time'")
    type = models.CharField(max_length=10, choices=metric_type_list())
    
    full = models.PositiveSmallIntegerField(help_text="article page views")
    abstract = models.PositiveSmallIntegerField(help_text="article abstract page views")
    digest = models.PositiveSmallIntegerField(help_text="article digest page views")
    pdf = models.PositiveSmallIntegerField(help_text="pdf downloads")

    class Meta:
        unique_together = ('article', 'date', 'type')

    def __unicode__(self):
        return '%s,%s,%s,%s' % (self.article, self.date, self.full, self.pdf)

    def __repr__(self):
        return u'<GAMetric %s>' % self.__unicode__()
