from django.db.models import Model, CharField, ForeignKey, PositiveIntegerField, DateField, CASCADE

PAGE_TYPES = BLOG, EVENT, INTERVIEW, LABS, PRESS = [
    'blog-article', 'event', 'interview', 'labs-post', 'press-package'
]

def page_type_choices():
    return zip(PAGE_TYPES, PAGE_TYPES)

class PageType(Model):
    name = CharField(primary_key=True, max_length=255, choices=page_type_choices())

class Page(Model):
    type = ForeignKey(PageType, on_delete=CASCADE)
    identifier = CharField(max_length=255)

    class Meta:
        unique_together = (('type', 'identifier'),)

class PageCount(Model):
    page = ForeignKey(Page, on_delete=CASCADE)
    views = PositiveIntegerField()
    date = DateField()
