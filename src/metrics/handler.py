from datetime import timedelta
from os.path import join
from django.conf import settings
import inspect
import uuid
from metrics import utils
from metrics.utils import ensure, lfilter
import requests, requests_cache
import logging

requests_cache.install_cache(**{
    'cache_name': join(settings.OUTPUT_PATH, 'db'),
    'backend': 'sqlite',
    'fast_save': True,
    'extension': '.sqlite3',
    # https://requests-cache.readthedocs.io/en/latest/user_guide.html#expiration
    'expire_after': timedelta(hours=24 * settings.CACHE_EXPIRY)
})

def clear_cache():
    requests_cache.clear()

LOG = logging.getLogger('debugger') # ! logs to a different file at a finer level

def opid(nom=''):
    "return a unique id to track a set of operations"
    # ll: pmc--20170101-235959--48029843290842903824930
    return '--'.join(lfilter(None, [nom, utils.ymdhms(), str(uuid.uuid4())]))

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

def ignore_handler(id, err):
    "does absolutely nothing"
    pass

def logit_handler(id, err):
    "writes a comprehensive log entry to a file"
    # err ll: {'request': <PreparedRequest [GET]>, 'response': <Response [404]>}
    payload = {
        'request': err.request.__dict__,
        'response': err.response.__dict__
    }
    fname = writefile(id, utils.lossy_json_dumps(payload), 'log')
    body = err.response.content
    fname2 = writefile(id, body, 'body')
    ctx = {
        'id': id,
        'logged': [fname, fname2],
    }
    LOG.warn("non-2xx response %s" % err, extra=ctx)

def raise_handler(id, err):
    "logs the error and then raises it again to be handled by the calling function"
    logit_handler(id, err)
    raise err

RAISE, IGNORE, LOGIT = 'raise', 'ignore', 'log'
HANDLERS = {
    RAISE: raise_handler,
    IGNORE: ignore_handler,
    LOGIT: logit_handler
}
DEFAULT_HANDLER = raise_handler

MAX_RETRIES = 3

def requests_get(*args, **kwargs):
    id = kwargs.pop('opid', opid())
    ctx = {
        'id': id
    }
    handler_opts = kwargs.pop('opts', {})

    # set any defaults for requests here
    default_kwargs = {
        'timeout': (3.05, 9), # connect time out, read timeout
    }
    default_kwargs.update(kwargs)
    kwargs = default_kwargs

    try:
        # http://docs.python-requests.org/en/master/api/#request-sessions
        session = requests.Session()
        adaptor = requests.adapters.HTTPAdapter(max_retries=MAX_RETRIES)
        session.mount('https://', adaptor)

        resp = session.get(*args, **kwargs)
        resp.raise_for_status()
        return resp

    except requests.HTTPError as err:
        # non 2xx response
        LOG.warn("error response attempting to fetch remote resource: %s" % err, extra=ctx)

        # these can be handled by passing in an 'opts' kwarg ll:
        # {404: handler.LOGIT}
        status_code = err.response.status_code
        code = handler_opts.get(status_code)
        # supports custom handlers like {404: lambda id, err: print(id, err)}
        fn = code if callable(code) else HANDLERS.get(code, DEFAULT_HANDLER)
        fn(id, err)

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
