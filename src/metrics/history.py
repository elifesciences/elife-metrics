from article_metrics.utils import lmap
from datetime import datetime, date
from django.conf import settings
import json
import logging
from article_metrics.utils import ensure

LOG = logging.getLogger(__name__)

# --- validation

def only_one_optional_date(d):
    return d['starts'] or d['ends']

def no_lonesome_redirect_prefix(data):
    return ('path-map' in data or 'path-map-file' in data) if 'redirect-prefix' in data else True

def exactly_one(d, *keys):
    return [k in d for k in keys].count(True) == 1

def exactly_one_if_any(d, *keys):
    return [k in d for k in keys].count(True) in [0, 1]

def path_map_or_file_not_both(data):
    return exactly_one_if_any(data, 'path-map', 'path-map-file')

def optional_ymd_date(key, val):
    if val is None:
        return
    if isinstance(val, str):
        try:
            datetime.strptime(val, "%Y-%m-%d")
        except ValueError as ve:
            raise AssertionError("frame field %r with value %r cannot be parsed as a datetime: %s" % (key, val, str(ve)))

def isa(thing):
    def _isa(key, val):
        ensure(isinstance(val, thing), "frame field %r is not a valid %r: %s" % (key, thing, val))
    return _isa

def dict_of_strings(key, val):
    ensure(isinstance(val, dict), "expected a dict")
    ensure(all(map(lambda key: isinstance(key, str) and key != "", val.keys())), "dictionary %r contains non-string fields: %s" % (key, list(val.keys())))

def validate_frame_data(frame_data):
    required_keys = [
        'starts', 'ends', 'id'
    ]
    ensure(all(map(lambda required_key: required_key in frame_data, required_keys)), "frame data missing required keys: %s" % frame_data)

    key_validators = {
        'starts': optional_ymd_date,
        'ends': optional_ymd_date,
        'id': isa(int),
        'comment': isa(str),
        'prefix': isa(str),
        'pattern': isa(str),
        'path-map': dict_of_strings, # todo: ensure is a map of strings, allow for an empty string for landing page
        'path-map-file': isa(str),
        'redirect-prefix': isa(str)
    }
    for key, val in frame_data.items():
        validator_fn = key_validators.get(key)
        if validator_fn:
            validator_fn(key, val)

    validators = [
        only_one_optional_date,
        no_lonesome_redirect_prefix,
        path_map_or_file_not_both
    ]
    for validator_fn in validators:
        validator_fn(frame_data)

    return True

def validate_history_data(history_data):
    d = history_data
    ensure(isinstance(d, dict), "history data is not a map")
    ensure(all(map(lambda key: key and isinstance(key, str), d.keys())), "history data contains empty or non-string keys")
    ensure(all(map(lambda val: isinstance(val, dict), d.values())), "history data contains keys with non-map data")
    ensure(all(map(lambda val: 'frames' in val, d.values())), "history data contains keys with missing 'frames' field")
    ensure(all(map(lambda val: isinstance(val['frames'], list), d.values())), "history data contains non-list 'frames' data")

    for key, val in history_data.items():
        for frame_data in val['frames']:
            ensure(validate_frame_data(frame_data), "history data %r contains invalid 'frames' field: %s" % (key, frame_data))

    return True

# --- coercion

def frames_wrangler(frame_list):

    def fill_empties(frame):
        frame['starts'] = frame['starts'] or settings.INCEPTION.date()
        frame['ends'] = frame['ends'] or date.today()
        return frame

    frame_list = lmap(fill_empties, frame_list)
    frame_list = sorted(frame_list, key=lambda f: f['starts']) # ASC

    return frame_list

def coerce_ymd_date(val):
    """transform `val` into a Python datetime.date object.
    returns `None` if `val` is empty."""
    if val:
        return datetime.strptime(val, "%Y-%m-%d").date()
    return None

def coerce_frame_data(frame_data):
    "transform the (validated) `frame_data`, returning a new dictionary."
    key_coercers = {
        'id': str,
        'starts': coerce_ymd_date,
        'ends': coerce_ymd_date,
    }
    new_data = {}
    for key, val in frame_data.items():
        if key in key_coercers:
            new_data[key] = key_coercers[key](val)
        else:
            new_data[key] = val
    return new_data

def coerce_frames_list(frames_list):
    "transform the (validated) `frames_list` data."
    coercions = [
        lambda fl: list(map(coerce_frame_data, frames_list)),
        frames_wrangler,
        # TODO: ensure no overlaps between frames
    ]
    print(frames_list)
    for coercer in coercions:
        frames_list = coercer(frames_list)

    return frames_list

def coerce_history_data(history_data):
    "transform the (validated) `history_data`"
    key_coercers = {
        'frames': coerce_frames_list
    }
    new_data = {}
    for toplevel_key, val_map in history_data.items():
        for key, val in val_map.items():
            if key in key_coercers:
                new_data[key] = key_coercers[key](val)
            else:
                new_data[key] = val
        history_data[toplevel_key] = new_data
    return history_data

# --- interface

def load_from_file(history_path=None):
    history_path = history_path or settings.GA_PTYPE_HISTORY_PATH
    try:
        history_data = json.load(open(history_path, 'r'))
        ensure(validate_history_data(history_data), "failed to validate history data")
        return coerce_history_data(history_data)
    except AssertionError as err:
        LOG.error("history is invalid: %s", str(err))
        raise

def ptype_history(ptype, history=None):
    history = history or load_from_file()
    ensure(ptype in history, "no historical data found: %s" % ptype, ValueError)
    return history[ptype]
