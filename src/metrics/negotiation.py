"""Adds a list of supported media types to Django REST so it
doesn't spaz out when you ask for a custom media article in the
Accept header."""

from rest_framework.renderers import JSONRenderer
from .utils import lmap

def mktype(row):
    nom, mime, version_list = row
    klass_list = lmap(lambda ver: ("%sVersion%s" % (nom, ver), "%s; version=1" % mime), version_list)
    global_scope = globals()

    def gen_klass(klass_row):
        nom, mime = klass_row
        global_scope[nom] = type(nom, (JSONRenderer,), {'media_type': mime})
    lmap(gen_klass, klass_list)

_dynamic_types = [
    # class name, media type, known version list
    ('Citation', 'application/vnd.elife.metric-citations+json', [1]),
    ('MetricTimePeriod', 'application/vnd.elife.metric-time-period+json', [1]),
]

lmap(mktype, _dynamic_types)
