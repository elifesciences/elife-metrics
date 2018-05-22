from copy import deepcopy
from article_metrics.utils import merge
from schema import Schema, And, Or, Use as Cast, Optional
from datetime import date
from functools import partial

type_optional_date = Or(date, None)
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

type_frame = Or(frame0, frame1, frame2, frame3)

type_object = Schema({
    'frames': [type_frame],
    Optional('examples'): [type_str]
})

type_history = Schema({type_str: type_object})
