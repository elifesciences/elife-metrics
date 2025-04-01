from urllib3.util.retry import Retry
from os.path import join
from django.conf import settings
import inspect
import uuid
from article_metrics import utils
import requests, requests_cache
import logging

from typing import Optional

LOG = logging.getLogger('debugger') # ! logs to a different file at a finer level

def clear_expired():
    requests_cache.remove_expired_responses()
    return settings.CACHE_NAME

def clear_cache():
    # completely empties the requests-cache database, probably not what you intended
    requests_cache.clear()

def opid(nom=''):
    "return a unique id to track a set of operations"
    # "pmc--2017-01-01-23-59-59--2fb4be3a-911f-4e83-a590-df8ae2c8d691"
    # "2017-01-01-23-59-59--2fb4be3a-911f-4e83-a590-df8ae2c8d691"
    return '--'.join(x for x in [nom, utils.ymdhms(), str(uuid.uuid4())] if x)

def fqfn(fn):
    mod = inspect.getmodule(fn)
    return '.'.join([mod.__name__, fn.__name__])

def writefile(xid, content, fname):
    path = join(settings.DUMP_PATH, xid)
    utils.ensure(utils.mkdirs(path), "failed to create path %s" % path)
    path = join(path, fname) # ll: /tmp/elife-metrics/pmc-asdfasdfasdf-482309849230/log
    if isinstance(content, str):
        content = content.encode('utf8')
    open(path, 'wb').write(content)
    return path

#
#
#

class NoneObj(object):
    pass

def ignore_handler(xid, err):
    "does absolutely nothing"
    pass

def logit_handler(xid, err):
    "writes a comprehensive log entry to a file"
    # err ll: {'request': <PreparedRequest [GET]>, 'response': <Response [404]>}
    payload = {
        'request': err.request.__dict__,
        'response': err.response.__dict__
    }
    fname = writefile(xid, utils.lossy_json_dumps(payload), 'log')
    body = err.response.content
    fname2 = writefile(xid, body, 'body')
    ctx = {
        'id': xid,
        'logged': [fname, fname2],
    }
    LOG.warning("non-2xx response %s" % err, extra=ctx)

def raise_handler(xid, err):
    "logs the error and then raises it again to be handled by the calling function"
    logit_handler(xid, err)
    raise err

RAISE, IGNORE, LOGIT = 'raise', 'ignore', 'log'
HANDLERS = {
    RAISE: raise_handler,
    IGNORE: ignore_handler,
    LOGIT: logit_handler
}
DEFAULT_HANDLER = raise_handler

MAX_RETRIES = 5

def http_get_using_session(*args, session: requests.Session, **kwargs):
    print('session', session)
    xid = kwargs.pop('opid', opid())
    ctx = {
        'id': xid
    }
    handler_opts = kwargs.pop('opts', {})

    # "It’s a good practice to set connect timeouts to slightly larger than a multiple of 3,
    # which is the default TCP packet retransmission window."
    # - https://docs.python-requests.org/en/latest/user/advanced/#timeouts
    connect_timeout = 3.05 # seconds

    # "... the read timeout is the number of seconds the client will wait for the server to send
    # a response. (Specifically, it’s the number of seconds that the client will wait between bytes
    # sent from the server. In 99.9% of cases, this is the time before the server sends the first byte)."
    read_timeout = 9 # seconds

    # set any defaults for requests here
    default_kwargs = {
        # https://docs.python-requests.org/en/latest/api/#requests.request
        # "timeout (float or tuple)" (optional) - How many seconds to wait for the server to
        #                                         send data before giving up, as a float, or a
        #                                         (connect timeout, read timeout) tuple.
        'timeout': (connect_timeout, read_timeout),
    }
    default_headers = {
        'User-Agent': settings.USER_AGENT,
    }
    final_headers = utils.merge(default_headers, kwargs.pop('headers', {}))
    final_kwargs = utils.merge(default_kwargs, kwargs, {'headers': final_headers})

    try:  
        # lsh@2023-07-28: handle network errors better
        # - https://github.com/elifesciences/issues/issues/8386
        # - https://urllib3.readthedocs.io/en/stable/user-guide.html#retrying-requests
        # - https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry
        max_retries_obj = Retry(**{
            'total': MAX_RETRIES,
            'connect': MAX_RETRIES,
            'read': MAX_RETRIES,
            # How many times to retry on bad status codes.
            # These are retries made on responses, where status code matches status_forcelist.
            'status': MAX_RETRIES,
            'status_forcelist': [413, 429, 503, # defaults
                                500, 502, 504],
            # {backoff factor} * (2 ** {number of previous retries})
            # 0.5 => 1.0, 2.0, 4.0, 8.0, 16
            'backoff_factor': 0.5,
        })
        adaptor = requests.adapters.HTTPAdapter(max_retries=max_retries_obj)
        session.mount('https://', adaptor)
        resp = session.get(*args, **final_kwargs)
        resp.raise_for_status()
        return resp

    except requests.HTTPError as err:
        # non 2xx response
        LOG.warning("error response attempting to fetch remote resource: %s" % err, extra=ctx)

        # these can be handled by passing in an 'opts' kwarg ll:
        # {404: handler.LOGIT}
        status_code = err.response.status_code
        code = handler_opts.get(status_code)
        # supports custom handlers like {404: lambda id, err: print(id, err)}
        fn = code if callable(code) else HANDLERS.get(code, DEFAULT_HANDLER)
        fn(xid, err)

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
            'id': xid,
            'dt': utils.ymdhms(),
            'error': str(err),
            'request': (data.get('request') or NoneObj()).__dict__,
            'response': (data.get('response') or NoneObj()).__dict__,
        }
        fname = writefile(xid, utils.lossy_json_dumps(payload), 'log')
        ctx['logged'] = fname
        LOG.exception("unhandled network exception fetching request: %s" % err, extra=ctx)
        raise

    except BaseException:
        LOG.exception("unhandled exception", extra=ctx)
        raise

def requests_get(*args, requests_session: Optional[requests.Session] = None, **kwargs):
    if requests_session is not None:
        return http_get_using_session(*args, session=requests_session, **kwargs)
    if not settings.TESTING:
        session = utils.create_caching_session()
    else:
        session = requests.Session()
    with session:
        return http_get_using_session(*args, session=session, **kwargs)

def capture_parse_error(fn):
    """wrapper around a parse function that captures any errors to a special log for debugging.
    first argument to decorated function *must* be the data that is being parsed."""
    def wrap(data, *args, **kwargs):
        xid = opid()
        ctx = {
            'id': xid,
            'ns': fqfn(fn),
        }
        try:
            return fn(data, *args, **kwargs)

        except BaseException:
            payload = {'data': data, 'args': args, 'kwargs': kwargs}
            fname = writefile(xid, utils.lossy_json_dumps(payload), 'log')
            ctx['log'] = fname
            LOG.exception("unhandled error", extra=ctx)
            return {'bad': data}

    return wrap
