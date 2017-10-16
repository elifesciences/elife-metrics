import yaml
from collections import OrderedDict
import time
import os, json
import tempfile, shutil
from functools import wraps
import logging
from datetime import datetime
import dateutil
import dateutil.parser
import pytz

LOG = logging.getLogger(__name__)

lmap = lambda func, *iterable: list(map(func, *iterable))
lfilter = lambda func, *iterable: list(filter(func, *iterable))
keys = lambda d: list(d.keys())

def comp(*fns):
    "composes functions LEFT to RIGHT"
    def _comp(*args, **kwargs):
        res = fns[0](*args, **kwargs)
        for fn in fns[1:]:
            res = fn(res)
        return res
    return _comp

def yaml_loads(stream):
    loader_class = yaml.Loader
    object_pairs_hook = OrderedDict

    class OrderedLoader(loader_class):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)

def group(lst, keyfn):
    grps = {}
    for x in lst:
        # would this work?
        #grps.get(keyfn(x), []).append(x)
        key = keyfn(x)
        grp = grps.get(key, [])
        grp.append(x)
        grps[key] = grp
    return grps

'''
def eargs(fn):
    "expand-args. allows composing funcs that require multiple arguments"
    @wraps(fn)
    def wrapper(args):
        return fn(*args)
    return wrapper
'''

# http://stackoverflow.com/questions/3744451/is-this-how-you-paginate-or-is-there-a-better-algorithm
def paginate(seq, rowlen):
    for start in xrange(0, len(seq), rowlen):
        yield seq[start:start + rowlen]

def complement(pred):
    @wraps(pred)
    def wrapper(*args, **kwargs):
        return not pred(*args, **kwargs)
    return wrapper

def splitfilter(func, data):
    return filter(func, data), filter(complement(func), data)

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

def ensure(assertion, msg, Klass=AssertionError):
    """intended as a convenient replacement for `assert` statements that
    get compiled away with -O flags"""
    if not assertion:
        raise Klass(msg)

def pad_msid(msid):
    return str(int(msid)).zfill(5)

def doi2msid(doi):
    "doi to manuscript id used in EJP"
    prefix = '10.7554/elife.'
    ensure(doi.lower().startswith(prefix), "this doesn't look like an eLife doi: %s" % doi)
    stripped = doi[len(prefix):].lstrip('0')
    if not stripped:
        # some joker has given us 10.7554/eLife.00000
        stripped = '0' # lucky non-article '0'
    # handles dois like: 10.7554/eLife.09560.001
    return int(stripped.split('.')[0])

def msid2doi(msid):
    ensure(isint(msid), "given msid must be an integer: %r" % msid)
    return '10.7554/eLife.%05d' % int(msid)

def subdict(d, kl):
    return {k: v for k, v in d.items() if k in kl}

def exsubdict(d, kl):
    return {k: v for k, v in d.items() if k not in kl}

def fmtdt(dt, fmt="%Y-%m-%d"):
    if not dt:
        dt = utcnow()
    ensure(isinstance(dt, datetime), "datetime object expected, got %r" % type(dt))
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

    else:
        # ensure tz is UTC
        if dt.tzinfo != pytz.utc:
            LOG.debug("converting an aware dt that isn't in utc TO utc: %r", dt)
            return dt.astimezone(pytz.utc)
    return dt

def utcnow():
    "returns a UTC datetime stamp with a UTC timezone object attached"
    # there is a datetime.utcnow(), but it doesn't attach a timezone object
    return datetime.now(pytz.utc).replace(microsecond=0)

'''
def ymdhms(dt):
    "returns an rfc3339 representation of a datetime object"
    if dt:
        dt = todt(dt) # convert to utc, etc
        return rfc3339(dt, utc=True)
'''

#
# django utils
#

def create_or_update(Model, orig_data, key_list, create=True, update=True, update_check=False, commit=True, **overrides):
    inst = None
    created = updated = checked = False
    data = {}
    data.update(orig_data)
    data.update(overrides)
    try:
        # try and find an entry of Model using the key fields in the given data
        inst = Model.objects.get(**subdict(data, key_list))
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
        else:
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

# copied directly from lax
from django.db import transaction, IntegrityError
def atomic(fn):
    def wrapper(*args, **kwargs):
        result, rollback_key = None, 'dry run rollback'
        # NOTE: dry_run must always be passed as keyword parameter (dry_run=True)
        dry_run = kwargs.pop('dry_run', False)
        try:
            with transaction.atomic():
                result = fn(*args, **kwargs)
                if dry_run:
                    # `transaction.rollback()` doesn't work here because the `transaction.atomic()`
                    # block is expecting to do all the work and only rollback on exceptions
                    raise IntegrityError(rollback_key)
                return result
        except IntegrityError as err:
            message = err.args[0]
            if dry_run and message == rollback_key:
                return result
            # this was some other IntegrityError
            raise
    return wrapper
