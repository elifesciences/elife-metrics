from django.db.models import Model, CharField, ForeignKey, PositiveIntegerField, DateField, CASCADE

PAGE_TYPES = BLOG, EVENT, INTERVIEW, LABS, PRESS = [
    'blog-article', 'event', 'interview', 'labs-post', 'press-package'
]

LANDING_PAGE = ''

def page_type_choices():
    return zip(PAGE_TYPES, PAGE_TYPES)

class PageType(Model):
    name = CharField(primary_key=True, max_length=255, choices=page_type_choices())

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<PageType %r>' % self.__str__()

class Page(Model):
    type = ForeignKey(PageType, on_delete=CASCADE)
    identifier = CharField(max_length=255, blank=True) # blank ('') is the landing page

    class Meta:
        unique_together = (('type', 'identifier'),)

    def __str__(self):
        name = self.identifier or '[landing page]'
        return "%s: %s" % (self.type, name) # ll: 'event: pants'

    def __repr__(self):
        return "<Page '%s:%s'>" % (self.type, self.identifier) # ll: <Page 'event:pants'>

class PageCount(Model):
    page = ForeignKey(Page, on_delete=CASCADE)
    views = PositiveIntegerField()
    date = DateField()

    def __str__(self):
        return "%s: %d views" % (self.date.strftime('%Y-%m-%d'), self.views) # ll: '2018-01-01: 12 views'

    def __repr__(self):
        return "<PageCount '%s:%s'>" % (self.date.strftime('%Y-%m-%d'), self.views) # ll: <PageCount '2018-01-01:12'>
