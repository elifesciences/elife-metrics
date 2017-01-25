import logging

LOG = logging.getLogger(__name__)

lmap = lambda func, *iterable: list(map(func, *iterable))
lfilter = lambda func, *iterable: list(filter(func, *iterable))
keys = lambda d: list(d.keys())

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

def rest(x):
    return x[1:]

def ensure(assertion, msg, *args):
    """intended as a convenient replacement for `assert` statements that
    get compiled away with -O flags"""
    if not assertion:
        raise AssertionError(msg % args)

def doi2msid(doi):
    "doi to manuscript id used in EJP"
    prefix = '10.7554/eLife.'
    ensure(doi.startswith(prefix), "this doesn't look like an eLife doi: %s" % prefix)
    return doi[len(prefix):].lstrip('0')

def msid2doi(msid):
    assert isint(msid), "given msid must be an integer: %r" % msid
    return '10.7554/eLife.%05d' % int(msid)

def subdict(d, kl):
    return {k: v for k, v in d.items() if k in kl}

def exsubdict(d, kl):
    return {k: v for k, v in d.items() if k not in kl}

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
