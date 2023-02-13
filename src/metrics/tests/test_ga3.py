from . import base
from metrics import ga3, models, history

class Four(base.BaseCase):
    def test_generic_query_pattern(self):
        "dead simple usecase when you want full control of query to GA"
        frame = {'pattern': '/pants'} # this would be shooting yourself in the foot however
        expected = '/pants' # a list of GA queries typically, but we can get away with the bare minimum
        self.assertEqual(ga3.generic_query_processor('', frame), expected)

    def test_generic_query_prefix(self):
        "a simple 'prefix' and nothing else will get you a basic 'landing page and sub-contents' type query"
        prefix = '/pants'
        frame = {'prefix': prefix}
        expected = ga3.generic_ga_filter('/pants') # ll: "ga:pagePath=~^{prefix}$,ga:pagePath=~^{prefix}/.*$"
        self.assertEqual(ga3.generic_query_processor('', frame), expected)

    def test_generic_query_prefix_list(self):
        "a 'prefix' and a list of subpaths will get you a landing page and enumerated sub-paths query"
        prefix = '/pants'
        frame = {'prefix': prefix, 'path-list': ['foo', 'bar', 'baz']}
        expected = "ga:pagePath=~^/pants$,ga:pagePath=~^/pants/foo$,ga:pagePath=~^/pants/bar$,ga:pagePath=~^/pants/baz$"
        self.assertEqual(ga3.generic_query_processor('', frame), expected)

    def test_generic_query_prefix_list__collections(self):
        "essentially a duplicate test, but using actual data"
        collection = history.ptype_history(models.COLLECTION)
        frame = collection['frames'][0]
        # I do not endorse this official-but-awful method of string concatenation
        expected = 'ga:pagePath=~^/collections/chemical-biology$' \
                   ',ga:pagePath=~^/collections/tropical-disease$' \
                   ',ga:pagePath=~^/collections/paleontology$' \
                   ',ga:pagePath=~^/collections/human-genetics$' \
                   ',ga:pagePath=~^/interviews/working-lives$' \
                   ',ga:pagePath=~^/collections/natural-history-model-organisms$' \
                   ',ga:pagePath=~^/natural-history-of-model-organisms$' \
                   ',ga:pagePath=~^/collections/reproducibility-project-cancer-biology$' \
                   ',ga:pagePath=~^/collections/plain-language-summaries$' \
                   ',ga:pagePath=~^/interviews/early-career-researchers$'
        actual = ga3.generic_query_processor(models.COLLECTION, frame)
        self.assertEqual(actual, expected)
