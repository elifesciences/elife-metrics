import time
import os, json, copy
import tempfile, shutil
from functools import wraps, partial, reduce
import logging
from datetime import datetime, date
import dateutil
import dateutil.parser
import pytz

LOG = logging.getLogger(__name__)

lmap = lambda func, *iterable: list(map(func, *iterable))
lfilter = lambda func, *iterable: list(filter(func, *iterable))
keys = lambda d: list(d.keys())

class ParseError(ValueError):
    pass

def comp(*fns):
    "composes functions LEFT to RIGHT"
    def _comp(*args, **kwargs):
        res = fns[0](*args, **kwargs)
        for fn in fns[1:]:
            res = fn(res)
        return res
    return _comp

# http://stackoverflow.com/questions/3744451/is-this-how-you-paginate-or-is-there-a-better-algorithm
def paginate(seq, rowlen):
    for start in range(0, len(seq), rowlen):
        yield seq[start:start + rowlen]

def complement(pred):
    @wraps(pred)
    def wrapper(*args, **kwargs):
        return not pred(*args, **kwargs)
    return wrapper

def splitfilter(func, data):
    return lfilter(func, data), lfilter(complement(func), data)

def flatten(nested_list):
    return [item for sublist in nested_list for item in sublist]

def isint(v):
    try:
        int(v)
        return True
    except (ValueError, TypeError):
        return False

def nth(idx, x):
    # 'nth' implies a sequential collection
    if isinstance(x, dict):
        raise TypeError
    if x is None:
        return x
    try:
        return x[idx]
    except IndexError:
        return None
    except TypeError:
        raise

def first(x):
    return nth(0, x)

def second(x):
    return nth(1, x)

def firstnn(x):
    "given sequential `x`, returns the first non-nil value"
    return first(lfilter(None, x))

def rest(x):
    return x[1:]

def ensure(assertion, msg, exception_class=AssertionError):
    """intended as a convenient replacement for `assert` statements that
    get compiled away with -O flags"""
    if not assertion:
        raise exception_class(msg)

def pad_msid(msid):
    return str(int(msid)).zfill(5)

def doi2msid(doi, safe=False, allow_subresource=True):
    "doi to manuscript id used in EJP"
    try:
        ensure(isinstance(doi, str), "unparseable elife doi, expecting a string, got %s" % type(doi))
        prefix = '10.7554/elife.'
        ensure(doi.lower().startswith(prefix), "unparseable elife doi, unrecognised prefix")
        stripped = doi[len(prefix):].lstrip('0')
        # handles dois like: 10.7554/eLife.09560.001
        bits = stripped.split('.', 1)
        if not allow_subresource:
            ensure(len(bits) == 1, "refusing to parse elife doi further, subresource detected")
        stripped = bits[0]
        ensure(isint(stripped), "unparseable elife doi, manuscript ID is not an integer")
        return int(stripped)
    except AssertionError:
        if safe:
            return None
        raise

def msid2doi(msid):
    ensure(isint(msid), "given msid must be an integer: %r" % msid)
    return '10.7554/eLife.%05d' % int(msid)

def subdict(d, kl):
    return {k: v for k, v in d.items() if k in kl}

def exsubdict(d, kl):
    return {k: v for k, v in d.items() if k not in kl}

# TODO: code smell, remove conditional
def fmtdt(dt, fmt="%Y-%m-%d"):
    if not dt:
        dt = utcnow()
    ensure(isinstance(dt, datetime) or isinstance(dt, date), "date or datetime object expected, got %r" % type(dt))
    return dt.strftime(fmt)

def ymdhms(dt=None):
    return fmtdt(dt, "%Y-%m-%d-%H-%M-%S")

def ymd(dt=None):
    "returns a simple YYYY-MM-DD representation of a datetime object"
    return fmtdt(dt)

def ym(dt=None):
    "returns a simple YYYY-MM representation of a datetime object"
    return fmtdt(dt, "%Y-%m")

def todt(val):
    "turn almost any formatted datetime string into a UTC datetime object"
    if val is None:
        return None
    dt = val
    if not isinstance(dt, datetime):
        dt = dateutil.parser.parse(val, fuzzy=False)
    dt.replace(microsecond=0) # not useful, never been useful, will never be useful.

    if not dt.tzinfo:
        # no timezone (naive), assume UTC and make it explicit
        LOG.debug("encountered naive timestamp %r from %r. UTC assumed.", dt, val)
        return pytz.utc.localize(dt)

    # ensure tz is UTC
    if dt.tzinfo != pytz.utc:
        LOG.debug("converting an aware dt that isn't in utc TO utc: %r", dt)
        return dt.astimezone(pytz.utc)

    return dt

def tod(val):
    "return a date value"
    if not val:
        return None
    if isinstance(val, date):
        return val
    val = todt(val)
    return val.date()


def utcnow():
    "returns a UTC datetime stamp with a UTC timezone object attached"
    # there is a datetime.utcnow(), but it doesn't attach a timezone object
    return datetime.now(pytz.utc).replace(microsecond=0)

def renkeys(d, keypair_list):
    for old_key, new_key in keypair_list:
        d[new_key] = d[old_key]
        del d[old_key]

#
# django utils
#

def create_or_update(Model, orig_data, key_list=None, create=True, update=True, update_check=False, commit=True, **overrides):
    inst = None
    created = updated = checked = False
    data = {}
    data.update(orig_data)
    data.update(overrides)
    key_list = key_list or data.keys()
    key_list = subdict(data, key_list)
    try:
        # try and find an entry of Model using the key fields in the given data
        ensure(key_list, "refusing to fetch %s with empty keys: %s" % (str(Model), key_list))
        inst = Model.objects.get(**key_list)
        # object exists, otherwise DoesNotExist would have been raised

        # test if objects needs updating
        # requires a db fetch but may save a db update ...
        if update and update_check:
            try:
                Model.objects.get(**data) # we could also inspect properties I suppose ...
                # doesn't need updating
                update = False
            except Model.DoesNotExist:
                # needs updating
                pass
            finally:
                checked = True

        if update:
            [setattr(inst, key, val) for key, val in data.items()]
            updated = True
    except Model.DoesNotExist:
        if create:
            inst = Model(**data)
            created = True

    if (updated or created) and commit:
        inst.save()

    if created:
        LOG.info("%r created" % inst)

    if updated and checked:
        LOG.info("%r changed and was updated" % inst)

    if updated and not checked:
        LOG.info("%r updated" % inst)

    # it is possible to neither create nor update.
    # in this case if the model cannot be found then None is returned: (None, False, False)
    return (inst, created, updated)

# http://stackoverflow.com/questions/434287/what-is-the-most-pythonic-way-to-iterate-over-a-list-in-chunks
def partition(seq, size):
    res = []
    for el in seq:
        res.append(el)
        if len(res) == size:
            yield res
            res = []
    if res:
        yield res

def lossy_json_dumps(obj, **kwargs):
    "drop-in for json.dumps that handles unserialisable objects."
    def _handler(obj):
        if hasattr(obj, 'isoformat'):
            return ymdhms(obj)
        LOG.debug('Object of type %s with value of %s is not JSON serializable' % (type(obj), repr(obj)))
        return '[unserialisable %s object]: %s' % (type(obj), str(obj))
    return json.dumps(obj, default=_handler, **kwargs)

def mkdirs(path):
    os.system('mkdir -p %s' % path)
    return os.path.exists(path)

def tempdir():
    # usage: tempdir, killer = tempdir(); killer()
    name = tempfile.mkdtemp()
    return (name, lambda: shutil.rmtree(name))

def listfiles(path, ext_list=None):
    "returns a list of absolute paths for given dir"
    path_list = map(lambda fname: os.path.abspath(os.path.join(path, fname)), os.listdir(path))
    if ext_list:
        path_list = lfilter(lambda path: os.path.splitext(path)[1] in ext_list, path_list)
    return sorted(filter(os.path.isfile, path_list))

# modified from:
# http://stackoverflow.com/questions/9323749/python-check-if-one-dictionary-is-a-subset-of-another-larger-dictionary
def partial_match(patn, real):
    """does real dict match pattern?"""
    for pkey, pvalue in patn.items():
        if isinstance(pvalue, dict):
            partial_match(pvalue, real[pkey]) # recurse
        else:
            ensure(real[pkey] == pvalue, "%s != %s" % (real[pkey], pvalue))
    return True

#
#
#

# don't use if we ever go concurrent
# http://blog.gregburek.com/2011/12/05/Rate-limiting-with-decorators/
# https://stackoverflow.com/questions/667508/whats-a-good-rate-limiting-algorithm/667706#667706
def simple_rate_limiter(maxPerSecond):
    minInterval = 1.0 / float(maxPerSecond)

    def decorate(func):
        lastTimeCalled = [0.0]

        def rateLimitedFunction(*args, **kargs):
            elapsed = time.clock() - lastTimeCalled[0]
            leftToWait = minInterval - elapsed
            if leftToWait > 0:
                time.sleep(leftToWait)
            ret = func(*args, **kargs)
            lastTimeCalled[0] = time.clock()
            return ret
        return rateLimitedFunction
    return decorate

#
#
#

def has_key(key, data=None):
    if data:
        return key in data
    return partial(has_key, key)

# expensive
def merge(*dicts):
    def _merge(a, b):
        c = copy.deepcopy(a)
        c.update(copy.deepcopy(b))
        return c
    return reduce(_merge, dicts)
