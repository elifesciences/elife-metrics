"""Adds a list of supported media types to Django REST so it
doesn't spaz out when you ask for a custom media article in the
Accept header."""

from rest_framework.renderers import JSONRenderer

def mktype(row):
    nom, mime, version_list = row
    klass_list = [("%sVersion%s" % (nom, ver), "%s; version=1" % mime) for ver in version_list]
    global_scope = globals()

    def gen_klass(klass_row):
        nom, mime = klass_row
        global_scope[nom] = type(nom, (JSONRenderer,), {'media_type': mime})
    [gen_klass(klass) for klass in klass_list]

_dynamic_types = [
    # class name, media type, known version list
    ('Citation', 'application/vnd.elife.metric-citations+json', [1]),
    ('MetricTimePeriod', 'application/vnd.elife.metric-time-period+json', [1]),
]

[mktype(_type) for _type in _dynamic_types]
