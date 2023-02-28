from article_metrics.ga_metrics.core import GA4_SWITCH
from article_metrics.utils import lmap
from schema import Schema, And, Or, Use as Coerce, Optional, SchemaError
from datetime import datetime, date, timedelta
from django.conf import settings
import logging
from article_metrics.utils import ensure

LOG = logging.getLogger(__name__)

one_day = timedelta(days=1)

HISTORY_DATA = {
    'blog-article': {
        'frames': [
            {'starts': GA4_SWITCH,
             'ends': None,
             'id': 3,
             'prefix': '/inside-elife'},

            {'starts': '2017-06-01',
             'ends': GA4_SWITCH - one_day,
             'id': 2,
             'prefix': '/inside-elife'},

            {'starts': '2014-02-01',
             'ends': '2017-05-31',
             'id': 1,
             'path-map-file': 'blog-article-path-map.txt',
             'pattern': 'ga:pagePath=~^/[a-z0-9-]+$,ga:pagePath==/elife-news,ga:pagePath=~^/elife-news/.*',
             'redirect-prefix': '/inside-elife'}]},

    'collection': {
        'frames': [
            {'starts': GA4_SWITCH,
             'ends': None,
             'id': 3,
             'prefix': '/collections'},

            {'starts': '2017-06-01',
             'ends': GA4_SWITCH - one_day,
             'id': 2,
             'prefix': '/collections'},

            {'starts': None,
             'ends': '2017-05-31',
             'id': 1,
             'path-map': {'/collections/chemical-biology': '0b5a36bb',
                          '/collections/tropical-disease': '2d2e35c4',
                          '/collections/paleontology': '2df5cbe1',
                          '/collections/human-genetics': '7eac161a',
                          '/interviews/working-lives': '88b9994b',
                          '/collections/natural-history-model-organisms': '8de90445',
                          '/natural-history-of-model-organisms': '8de90445',
                          '/collections/reproducibility-project-cancer-biology': '9b1e83d1',
                          '/collections/plain-language-summaries': '9e8f4a49',
                          '/interviews/early-career-researchers': 'fecda514'}}]},

    'digest': {
        'frames': [
            {'starts': GA4_SWITCH,
             'ends': None,
             'id': 2,
             'prefix': '/digests'},

            {'starts': '2017-09-01',
             'ends': GA4_SWITCH - one_day,
             'id': 1,
             'prefix': '/digests'}]},

    'event': {
        'frames': [
            {'starts': GA4_SWITCH,
             'ends': None,
             'id': 3,
             'prefix': '/events'},

            {'starts': '2017-06-01',
             'ends': GA4_SWITCH - one_day,
             'id': 2,
             'prefix': '/events'},

            {'starts': None,
             'ends': '2017-05-31',
             'id': 1,
             'path-map': {'/elife-news/events': '',
                          '/events/apply-now-attend-elife-peer-review-workshop-harvard-th-chan-school-public-health': '6a9313db',
                          '/events/apply-now-attend-elifestem-cell-reports-peer-review-workshop-isscr-2017': '6a9313db',
                          '/events/secure-your-space-elife-peer-review-workshop-harvard-th-chan-school-public-health': '6a9313db',
                          '/events/still-time-apply-elifestem-cell-reports-peer-review-workshop-isscr-2017': '6a9313db',
                          '/events/webinar-invitation-elife-peer-review-explained-randy-schekman': '0ec94dac'},
             'pattern': 'ga:pagePath=~^/elife-news/events$,ga:pagePath=~^/events$,ga:pagePath=~^/events/.*$'}]},

    'interview': {
        'frames': [
            {'starts': GA4_SWITCH,
             'ends': None,
             'id': 3,
             'prefix': '/interviews'},

            {'starts': '2017-06-01',
             'ends': GA4_SWITCH - one_day,
             'id': 2,
             'prefix': '/interviews'},

            {'starts': None,
             'ends': '2017-05-31',
             'id': 1,
             'path-map-file': 'interview-path-map.txt',
             'redirect-prefix': '/interviews'}]},

    'labs-post': {
        'frames': [
            {'starts': GA4_SWITCH,
             'ends': None,
             'id': 3,
             'prefix': '/labs'},

            {'starts': '2017-06-01',
             'ends': GA4_SWITCH - one_day,
             'id': 1, # todo: shouldn't this be 2?
             'prefix': '/labs'},

            {'starts': '2015-08-01',
             'ends': '2017-05-31',
             'id': 2,
             'path-map': {'/elife-news/authoring-online-lens-writer': '417bcedc',
                          '/elife-news/colab-instant-messaging-scientists': '75edb315',
                          '/elife-news/composing-reproducible-manuscripts-using-r-markdown': 'cad57bcf',
                          '/elife-news/elife-labs-presenting-proteopedia-sharing-macromolecule-concepts-online': 'a9c66d96',
                          '/elife-news/elife-labs-what-manuscripts': '0f2f45d5',
                          '/elife-news/hack-cambridge-recurse-entries-explore-knowledge-direct-scichat': 'cb73dd25',
                          '/elife-news/international-image-interoperability-framework-iiif-science-publishers': 'aabe94cd',
                          '/elife-news/introducing-lens-writer': '417bcedc',
                          '/elife-news/introducing-our-new-experiment-lens-writer': '417bcedc',
                          '/elife-news/labs': '',
                          '/elife-news/proteopedia-sharing-macromolecule-concepts-online': 'a9c66d96',
                          '/elife-news/toward-publishing-reproducible-computation-binder': 'a7d53a88',
                          '/elife-news/what-is-manuscripts': '0f2f45d5',
                          '/elife-news/writing-scholarly-documents-manuscripts': '0f2f45d5'}}]},

    'press-package': {
        'frames': [
            {'starts': GA4_SWITCH,
             'ends': None,
             'id': 3,
             'prefix': '/for-the-press'},

            {'starts': '2017-06-01',
             'ends': GA4_SWITCH - one_day,
             'id': 2,
             'prefix': '/for-the-press'},

            {'starts': None,
             'ends': '2017-05-31',
             'id': 1,
             'path-map-file': 'press-package-path-map.txt',
             'prefix': '/elife-news',
             'redirect-prefix': '/for-the-press'}]}}

# --- spec

def date_wrangler(v):
    if isinstance(v, str):
        return datetime.strptime(v, "%Y-%m-%d").date()
    if isinstance(v, datetime):
        return v.date()
    return v

def frames_wrangler(frame_list):

    def fill_empties(frame):
        frame['starts'] = frame['starts'] or settings.INCEPTION.date()
        frame['ends'] = frame['ends'] or date.today()
        return frame

    frame_list = lmap(fill_empties, frame_list)
    frame_list = sorted(frame_list, key=lambda f: f['starts']) # ASC

    # TODO: ensure no overlaps between frames

    return frame_list

type_optional_date = Or(Coerce(date_wrangler), None)
type_str = And(str, len) # non-empty string

only_one_optional_date = lambda d: d['starts'] or d['ends']
no_lonesome_redirect_prefix = lambda data: ('path-map' in data or 'path-map-file' in data) if 'redirect-prefix' in data else True

def exactly_one(d, *keys):
    return [k in d for k in keys].count(True) == 1

def exactly_one_if_any(d, *keys):
    return [k in d for k in keys].count(True) in [0, 1]

def path_map_or_file_not_both(data):
    return exactly_one_if_any(data, 'path-map', 'path-map-file')

type_frame = {
    'starts': type_optional_date,
    'ends': type_optional_date,
    'id': And(Coerce(str), type_str),
    Optional('comment'): type_str,

    # request processing
    Optional('prefix'): type_str,
    Optional('pattern'): type_str,

    # response processing
    Optional('path-map'): {type_str: str}, # allow empty strings here (landing pages)
    Optional('path-map-file'): type_str,
    Optional('redirect-prefix'): type_str,
}
type_frame = And(type_frame, only_one_optional_date, no_lonesome_redirect_prefix, path_map_or_file_not_both)

type_object = Schema({
    'frames': And([type_frame], Coerce(frames_wrangler))
})

type_history = Schema({type_str: type_object})

# ---

def load_history():
    try:
        return type_history.validate(HISTORY_DATA)
    except SchemaError as err:
        LOG.error("history is invalid: %s", str(err))
        raise

def ptype_history(ptype, history=None):
    history = history or load_history()
    ensure(ptype in history, "no historical data found: %s" % ptype, ValueError)
    return history[ptype]
