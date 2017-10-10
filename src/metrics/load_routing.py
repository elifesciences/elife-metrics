import re
from StringIO import StringIO
import utils
from utils import ensure

def parse(name, body):
    retval = {'name': name, 'pattern': body['path']}
    path = body['path']

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

    pattern = "^%s$" % path
    ga_pattern = "ga:pagePath=~" + pattern
    
    if len(pattern) > 128 and '|' in pattern:
        # this regex is too damn long. in some cases we can explode patterns
        # in this case, we're looking for patterns like '/(foo|bar|baz|bup)/' to explode
        regex2 = r"\([()\w|-]+\)" # regex matching regex
        matches = re.finditer(regex2, pattern)
        match = next(matches)
        if not match:
            raise ValueError("failed to reduce size of regular expression. GA will refuse to run this query: %s" % ga_pattern)
        
        subs = []
        match = match.group()
        subs = match.strip('()').split('|') # explode
        subs = map(lambda sub: ga_pattern.replace(match, sub), subs)

        # final check nothing is huge
        map(lambda sub: ensure(len(sub) <= 128, "GA requires a pattern 128 characters or less: %s" % sub), subs)

        # make a super long expression
        ga_pattern = ",".join(subs)
    
    retval['pattern'] = ga_pattern
    return retval

def loads(string):
    raw = utils.yaml_loads(StringIO(string))
    ensure(isinstance(raw, dict), "dictionary expected after deserialising", ValueError)
    return [parse(name, rest) for name, rest in raw.items()]
