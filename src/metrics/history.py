from article_metrics.utils import lmap
from schema import Schema, And, Or, Use as Coerce, Optional, SchemaError
from datetime import datetime, date
from django.conf import settings
import json
import logging
from collections import OrderedDict
from article_metrics.utils import ensure

LOG = logging.getLogger(__name__)

def date_wrangler(v):
    if isinstance(v, str):
        return datetime.strptime(v, "%Y-%m-%d").date()
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
    r = [k in d for k in keys]
    return r.count(True) in [0, 1]

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


def load_from_file(history_path=None):
    history_path = history_path or settings.GA_PTYPE_HISTORY_PATH
    try:
        history_data = json.load(open(history_path, 'r'), object_pairs_hook=OrderedDict)
        return type_history.validate(history_data)
    except SchemaError as err:
        LOG.error("history is invalid: %s", str(err))
        raise

def ptype_history(ptype, history=None):
    history = history or load_from_file()
    ensure(ptype in history, "no historical data found: %s" % ptype, ValueError)
    return history[ptype]
