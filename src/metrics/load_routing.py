import os, json
import requests
import re
from StringIO import StringIO
import utils
from utils import ensure, lfiltermap
from django.conf import settings
from kids.cache import cache
import logging
from urlparse import urlparse

LOG = logging.getLogger(__name__)

JOURNAL_INCEPTION = '2017-01-01'

def path_to_regex(path):
    return "^%s$" % path

def frame(pattern, starts=None, ends=None):
    return {
        'pattern': pattern,
        'starts': starts,
        'ends': ends
    }


#
# journal routing
#

def parse(name, body):
    "each route in the journal routing file contains the canonical 'page' and a *current* path"
    path = body['path']

    # the path becomes a regular expression.
    # certain cases need to be escaped while we're still dealing with simple placeholders
    # re.escape is overkill
    escaped = r'([.-])'
    path = re.sub(escaped, r'\\\1', path) # foo.bar => foo\.bar and foo-bar => foo\-bar

    if '{' in path:
        # path contains placeholders
        # replace placeholders with regular expressions
        # sometimes the regex os provided for us in the 'requirements' section
        requirements = body.get('requirements', {})
        # sometimes there are multiple placeholders
        regex = r"{(\w+)}"
        matches = re.finditer(regex, path)
        match_anything = '.+'
        # modify the path in-place until the groups are replaced with regex
        for match in matches:
            replacement = requirements.get(match.groups()[0], match_anything)
            path = path.replace(match.group(), replacement)

    retval = {'name': name, 'frames': [], 'examples': []}
    retval['frames'] = [frame(path_to_regex(path), JOURNAL_INCEPTION)]
    return retval

def excluded(path):
    exclusions = [
        '/articles',
        '/lookup/doi',
        '/download',
        '/ping'
    ]
    return any(map(lambda exc: path.startswith(exc), exclusions))

def load_journal_route_string(string):
    raw = utils.yaml_loads(StringIO(string))
    ensure(isinstance(raw, dict), "dictionary expected after deserialising", ValueError)
    return [parse(name, rest) for name, rest in raw.items() if not excluded(rest['path'])]

@cache
def load_journal_route_file(path):
    return load_journal_route_string(open(path, 'r').read())

#
# old journal redirects
#

def resolve(path):
    if path.startswith('http'):
        return None
    url = "https://elifesciences.org" + path
    LOG.info("resolving %s" % url)
    resp = requests.head(url, allow_redirects=True)
    url = resp.url
    return urlparse(url).path

def load_nginx_redirect_string(stringblob):
    "fully resolve any path - this will do ~2k+ requests to the elifesciences website"
    cache_file = settings.JOURNAL_REDIRECTS + '.json'
    if os.path.exists(settings.JOURNAL_REDIRECTS + '.json'):
        return json.load(open(cache_file, 'r'))

    def parse_line(string):
        string = string.strip()
        if not (string.startswith("'") and string.endswith(";")):
            return
        bits = string.split("' '")
        if len(bits) > 2:
            raise ValueError("unhandled redirect: %s" % string)
        return (bits[0].strip("'"), bits[1].strip("';"))

    redirects = dict(lfiltermap(parse_line, stringblob.splitlines()))
    redirects = {old: {'new': new, 'resolved': resolve(new)} for old, new in redirects.items()}
    return redirects

def load_nginx_redirect_file(path):
    return load_nginx_redirect_string(open(path, 'r').read())

'''
def synthetic_events():
    synthetic = [
        ('about-people-syn', {'path': '/about/people'}),
        ('event-syn', {'path': '/events/{id}'}),
        ('inside-elife-article-syn', {'path': '/inside-elife/{id}'}),
    ]
    return [parse(name, body) for name, body in synthetic]

def route_path(path):
    if not path:
        return

    routes = load_journal_route_file(settings.JOURNAL_ROUTES)
    # routes.extend(synthetic_events())

    for route in routes:
        if re.match(route['pattern'], path):
            return route

def old_paths_without_a_new_route():
    redirects = load_nginx_redirect_file(settings.JOURNAL_REDIRECTS)
    for old_path, new_path in redirects.items():
        if new_path['resolved'] and not route_path(new_path['resolved']):
            print json.dumps({'old': old_path, 'new': new_path['resolved']})

'''

def routing_table():
    "generates a route table with examples"
    routes = load_journal_route_file(settings.JOURNAL_ROUTES)
    redirects = load_nginx_redirect_file(settings.JOURNAL_REDIRECTS)

    route_idx = {r['name']: r for r in routes}

    def _route_path(path):
        for route in routes:
            # at this point, we have just the one frame
            pattern = route['frames'][0]['pattern']
            if re.match(pattern, path):
                return route

    for old_path, redirect in redirects.items():
        if redirect['resolved']:
            resolves_to = _route_path(redirect['resolved']) # 'resolved' is the new path that the old path now resolves to
            if resolves_to:
                route_idx[resolves_to['name']]['examples'].append(old_path)

    return route_idx

def dump_routing_table():
    "write the route table to disk"
    path = settings.ROUTE_TABLE
    json.dump(routing_table(), open(path, 'w'), indent=4)
    return path
