import base
from metrics import load_routing
from metrics import load_routing as lr

class One(base.BaseCase):
    def setUp(self):
        self.fixture = '''
about-peer-review:
    path: /about/peer-review
    defaults:
         _controller: AppBundle:About:peerReview

about-people:
    path: /about/people/{type}
    defaults:
         _controller: AppBundle:About:people
         type: ''

article-ris:
    path: /articles/{id}.ris
    defaults:
         _controller: AppBundle:Articles:ris
    requirements:
        id: '[a-z0-9-]+'

collection:
    path: /collections/{id}/{slug}
    defaults:
         _controller: AppBundle:Collections:collection
         slug: ''
    requirements:
        id: '[a-z0-9-]+'

        '''

    def tearDown(self):
        pass

    def test_exclusions(self):
        cases = [
            ('/about/peer-review', False),
            ('/about/people/{type}', False),
            ('/articles/{id}.ris', True),
            ('/collections/{id}/{slug}', False)
        ]
        for given, expected in cases:
            self.assertEqual(expected, load_routing.excluded(given))

    def test_load(self):
        expected = [
            {'frames': [{'pattern': '^/about/peer\\-review$', 'ends': None, 'starts': '2017-01-01'}], 'name': 'about-peer-review', 'examples': []},
            {'frames': [{'pattern': '^/about/people/.+$', 'ends': None, 'starts': '2017-01-01'}], 'name': 'about-people', 'examples': []},
            # excluded
            #{'frames': [{'pattern': '^/articles/[a-z0-9-]+\\.ris$', 'ends': None, 'starts': '2017-01-01'}], 'name': 'article-ris', 'examples': []},
            {'frames': [{'pattern': '^/collections/[a-z0-9-]+/.+$', 'ends': None, 'starts': '2017-01-01'}], 'name': 'collection', 'examples': []}
        ]
        self.assertEqual(expected, load_routing.load_journal_route_string(self.fixture))

    def test_long_pattern(self):
        "patterns longer than 128 chars are exploded"

        fixture = '''
foo-type:
    path: /foo/{type}
    defaults:
         _controller: AppBundle:ArticleTypes:list
    requirements:
        type: '(correction|editorial|feature|insight|research-advance|research-article|retraction|registered-report|replication-study|scientific-correspondence|short-report|tools-resources)'
        '''

        expected = lr.frame('foo-type')
        expected.update({
            'pattern': '^/foo/(correction|editorial|feature|insight|research-advance|research-article|retraction|registered-report|replication-study|scientific-correspondence|short-report|tools-resources)$',
            'ga_pattern': 'ga:pagePath=~^/foo/correction$,ga:pagePath=~^/foo/editorial$,ga:pagePath=~^/foo/feature$,ga:pagePath=~^/foo/insight$,ga:pagePath=~^/foo/research-advance$,ga:pagePath=~^/foo/research-article$,ga:pagePath=~^/foo/retraction$,ga:pagePath=~^/foo/registered-report$,ga:pagePath=~^/foo/replication-study$,ga:pagePath=~^/foo/scientific-correspondence$,ga:pagePath=~^/foo/short-report$,ga:pagePath=~^/foo/tools-resources$',
            'starts': lr.JOURNAL_INCEPTION
        })

        actual = lr.load_journal_route_string(fixture)[0]['frames'][0]
        self.assertEqual(expected, lr.gaify(actual))
