from article_metrics.utils import merge
from schema import Schema, And, Or, Use as Coerce, Optional, SchemaError
from datetime import datetime
#from kids.cache import cache as cached
from django.conf import settings
import json
import logging
from article_metrics.utils import ensure

LOG = logging.getLogger(__name__)

def to_date(v):
    if isinstance(v, str):
        return datetime.strptime(v, "%Y-%m-%d").date()
    return v

type_optional_date = Or(Coerce(to_date), None)
type_str = And(str, len) # non-empty string

_frame0 = {'starts': type_optional_date, 'ends': type_optional_date}
_only_one = lambda d: d['starts'] or d['ends']
frame0 = And(_frame0, _only_one) # we can't merge Schemas, which sucks

_frame1 = merge(_frame0, {'prefix': type_str})
frame1 = And(_frame1, _only_one)

_frame2 = merge(_frame1, {'path-list': [type_str]})
frame2 = And(_frame2, _only_one)

_frame3 = merge(_frame0, {'pattern': type_str})
frame3 = And(_frame3, _only_one)

type_frame = Or(frame1, frame2, frame3)

type_object = Schema({
    'frames': [type_frame],
    Optional('examples'): [type_str]
})

type_history = Schema({type_str: type_object})


#@cached
def load_from_file(history_path=None):
    history_path = history_path or settings.GA_PTYPE_HISTORY_PATH
    try:
        history_data = json.load(open(history_path, 'r'))
        return type_history.validate(history_data)
    except SchemaError as err:
        LOG.error("history is invalid: %s", str(err))
        raise

def ptype_history(ptype, history=None):
    history = history or load_from_file()
    # TODO: enshrine this rule in the schema somehow
    ensure(ptype in history, "no historical data found: %s" % ptype, ValueError)
    return history[ptype]
