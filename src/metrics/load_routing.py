from collections import OrderedDict
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
from ga_metrics import core as ga_core

LOG = logging.getLogger(__name__)

def path_to_regex(path):
    return "^%s$" % path

def frame(pattern, starts=None, ends=None):
    return {
        'pattern': pattern,
        'starts': starts,
        'ends': ends
    }

def explode_ga_pattern(pattern):
    ga_pattern = "ga:pagePath=~" + pattern

    # TODO: shift this into an 'explode' type function
    if len(pattern) > 128 and '|' in pattern:
        # this regex is too damn long. in some cases we can explode patterns
        # in this case, we're looking for patterns like '/(foo|bar|baz|bup)/' to explode
        regex2 = r"\([()\w|-]+\)" # regex matching regex
        matches = re.finditer(regex2, pattern)
        match = next(matches, None)
        if match:
            match = match.group()
            subs = match.strip('()').split('|') # explode
            subs = map(lambda sub: ga_pattern.replace(match, sub), subs)

            # final check nothing is huge
            map(lambda sub: ensure(len(sub) <= 128, "GA requires a pattern 128 characters or less: %s" % sub), subs)

            # make a super long expression
            ga_pattern = ",".join(subs)

        elif '$|^' in pattern:
            bits = pattern.split('|')
            subs = map(lambda bit: "ga:pagePath=~" + bit, bits)
            ga_pattern = ",".join(subs)

        else:
            raise ValueError("failed to reduce size of regular expression. GA will refuse to run this query: %s" % ga_pattern)

    ensure(len(ga_pattern) <= 4096, "%s\nexpression too large by %s bytes" % (ga_pattern, (len(ga_pattern) - 4096)))

    return ga_pattern


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
    retval['frames'] = [frame(path_to_regex(path), ga_core.SITE_SWITCH_v2)]
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
    ensure(isinstance(raw, OrderedDict), "ordered dictionary expected after deserialising", ValueError)
    return [parse(name, rest) for name, rest in raw.items() if not excluded(rest['path'])]

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

def load_custom_route_file(path):
    if os.path.exists(path):
        return json.load(open(path, 'r'))

def gaify(frame):
    frame['ga_pattern'] = explode_ga_pattern(frame['pattern'])
    return frame

@cache
def routing_table(routes=None):
    "generates a route table with examples"
    if not routes:
        routes = load_journal_route_file(settings.JOURNAL_ROUTES)
    custom_routes = load_custom_route_file(settings.CUSTOM_ROUTES)
    redirects = load_nginx_redirect_file(settings.JOURNAL_REDIRECTS)

    route_idx = OrderedDict([(r['name'], r) for r in routes])

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

    # add custom routes
    route_idx = utils.merge(route_idx, custom_routes)

    # generate regex for GA
    for name, route in route_idx.items():
        route_idx[name]['frames'] = map(gaify, route['frames'])

    return route_idx

'''
def gen_overrides():
    "create an example file that can be modified to provide overrides"
    route_idx = routing_table()
    return {key: {'frames': [frame("|".join(map(path_to_regex, val['examples'])), None, '2017-01-01')]} for key, val in route_idx.items()}
'''

def dump_routing_table():
    "write the route table to disk"
    path = settings.ROUTE_TABLE
    json.dump(routing_table(), open(path, 'w'), indent=4)
    return path
