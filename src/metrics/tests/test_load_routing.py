import base
from metrics import load_routing, models

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

    def test_load(self):
        expected = [
            {'name': 'about-peer-review', 'pattern': 'ga:pagePath=~^/about/peer\-review$'},
            {'name': 'about-people', 'pattern': 'ga:pagePath=~^/about/people/.+$'},
            {'name': 'article-ris', 'pattern': 'ga:pagePath=~^/articles/[a-z0-9-]+\.ris$'},
            {'name': 'collection', 'pattern': 'ga:pagePath=~^/collections/[a-z0-9-]+/.+$'}
        ]
        self.assertEqual(expected, load_routing.loads(self.fixture))

    def test_long_pattern(self):
        "patterns longer than 128 chars are exploded"
        
        fixture = '''
article-type:
    path: /articles/{type}
    defaults:
         _controller: AppBundle:ArticleTypes:list
    requirements:
        type: '(correction|editorial|feature|insight|research-advance|research-article|retraction|registered-report|replication-study|scientific-correspondence|short-report|tools-resources)'
        '''
        
        expected = [{'name': 'article-type', 'pattern': 'ga:pagePath=~^/articles/correction$,ga:pagePath=~^/articles/editorial$,ga:pagePath=~^/articles/feature$,ga:pagePath=~^/articles/insight$,ga:pagePath=~^/articles/research-advance$,ga:pagePath=~^/articles/research-article$,ga:pagePath=~^/articles/retraction$,ga:pagePath=~^/articles/registered-report$,ga:pagePath=~^/articles/replication-study$,ga:pagePath=~^/articles/scientific-correspondence$,ga:pagePath=~^/articles/short-report$,ga:pagePath=~^/articles/tools-resources$'}]
        
        self.assertEqual(expected, load_routing.loads(fixture))

    def test_pattern_loaded_into_db(self):
        ctypes = load_routing.loads(self.fixture)
        map(load_routing.insert, ctypes)
        self.assertEqual(len(ctypes), models.Page.objects.count())
