from os.path import join
from django.conf import settings
import inspect
import uuid
from metrics import utils
from metrics.utils import ensure
import requests
import logging

LOG = logging.getLogger('debugger') # ! logs to a different file at a finer level

def opid(nom=''):
    "return a unique id to track a set of operations"
    # ll: pmc--20170101-235959--48029843290842903824930
    return '--'.join(filter(None, [nom, utils.ymdhms(), str(uuid.uuid4())]))

def fqfn(fn):
    mod = inspect.getmodule(fn)
    return '.'.join([mod.__name__, fn.__name__])

def writefile(id, content, fname):
    path = join(settings.DUMP_PATH, id)
    ensure(utils.mkdirs(path), "failed to create path %s" % path)
    path = join(path, fname) # ll: /tmp/elife-metrics/pmc-asdfasdfasdf-482309849230/log
    open(path, 'w').write(content)
    return path

#
#
#

class NoneObj(object):
    pass

def requests_get(*args, **kwargs):
    id = kwargs.pop('opid', opid())
    ctx = {
        'id': id
    }
    try:
        # TODO: opportunity here for recovery from certain errors
        resp = requests.get(*args, **kwargs)
        resp.raise_for_status()
        return resp

    except requests.HTTPError as err:
        # non 2xx response
        # err ll: {'request': <PreparedRequest [GET]>, 'response': <Response [404]>}
        payload = {
            'request': err.request.__dict__,
            'response': err.response.__dict__
        }
        fname = writefile(id, utils.lossy_json_dumps(payload), 'log')
        body = err.response.content
        fname2 = writefile(id, body, 'body')
        ctx['logged'] = [fname, fname2]
        LOG.warn("non-2xx response %s" % err, extra=ctx)
        raise

    # handle more fine-grained errors here:
    # http://docs.python-requests.org/en/master/_modules/requests/exceptions/
    # except ConnectionError as err:
    #    pass

    # captures any requests exceptions not caught above
    except requests.RequestException as err:
        # all other requests-related exceptions
        # no request or response objects available for debug
        data = err.__dict__ # urgh, objects.
        payload = {
            'id': id,
            'dt': utils.ymdhms(),
            'error': str(err),
            'request': (data.get('request') or NoneObj()).__dict__,
            'response': (data.get('response') or NoneObj()).__dict__,
        }
        fname = writefile(id, utils.lossy_json_dumps(payload), 'log')
        ctx['logged'] = fname
        LOG.exception("unhandled network exception fetching request: %s" % err, extra=ctx)
        raise

    except BaseException as err:
        LOG.exception("unhandled exception", extra=ctx)
        raise


def capture_parse_error(fn):
    """wrapper around a parse function that captures any errors to a special log for debugger.
    first argument to decorated function *must* be the data that is being parsed."""
    def wrap(data, *args, **kwargs):
        id = opid()
        ctx = {
            'id': id,
            'ns': fqfn(fn),
        }
        try:
            return fn(data, *args, **kwargs)

        except BaseException:
            payload = {'data': data, 'args': args, 'kwargs': kwargs}
            fname = writefile(id, utils.lossy_json_dumps(payload), 'log')
            ctx['log'] = fname
            LOG.exception("unhandled error", extra=ctx)
            return {'bad': data}

    return wrap
