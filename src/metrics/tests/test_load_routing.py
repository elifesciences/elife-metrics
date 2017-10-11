import base
from mock import patch
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
            {'name': 'collection', 'pattern': 'ga:pagePath=~^/collections/[a-z0-9-]+/.+$'},
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

    def test_bad_pattern_not_loaded_into_db(self):
        ctypes = load_routing.loads(self.fixture)
        ctypes[0]['pattern'] = 'PANTS'
        self.assertRaises(ValueError, map, load_routing.insert, ctypes)

    def test_double_insert(self):
        ctypes = load_routing.loads(self.fixture)
        map(load_routing.insert, ctypes)
        self.assertEqual(len(ctypes), models.Page.objects.count())
        # results don't accumulate
        map(load_routing.insert, ctypes)
        self.assertEqual(len(ctypes), models.Page.objects.count())
        # even if you change their pattern
        ctypes[0]['pattern'] = "%s,%s" % tuple([ctypes[0]['pattern']] * 2)
        map(load_routing.insert, ctypes)
        self.assertEqual(len(ctypes), models.Page.objects.count())

    def test_call_ga(self):
        ctypes = load_routing.loads(self.fixture)
        page = load_routing.insert(ctypes[0])
        page = page[0] # ll: (obj, created?, updated?)

        ga_fixture = {u'kind': u'analytics#gaData', u'rows': [[u'/about/peer-review', u'440']], u'containsSampledData': False, u'profileInfo': {u'webPropertyId': u'UA-48379231-2', u'internalWebPropertyId': u'79882125', u'tableId': u'ga:82618489', u'profileId': u'82618489', u'profileName': u'All Web Site Data', u'accountId': u'48379231'}, u'itemsPerPage': 10000, u'totalsForAllResults': {u'ga:sessions': u'440'}, u'columnHeaders': [{u'dataType': u'STRING', u'columnType': u'DIMENSION', u'name': u'ga:pagePath'}, {u'dataType': u'INTEGER', u'columnType': u'METRIC', u'name': u'ga:sessions'}], u'query': {u'sort': [u'ga:pagePath'], u'max-results': 10000, u'dimensions': u'ga:pagePath', u'start-date': u'2017-01-01', u'start-index': 1, u'ids': u'ga:82618489', u'metrics': [u'ga:sessions'], u'filters': u'ga:pagePath=~^/about/peer\\-review$', u'end-date': u'2017-10-11'}, u'totalResults': 1, u'id': u'https://www.googleapis.com/analytics/v3/data/ga?ids=ga:82618489&dimensions=ga:pagePath&metrics=ga:sessions&sort=ga:pagePath&filters=ga:pagePath%3D~%5E/about/peer%5C-review$&start-date=2017-01-01&end-date=2017-10-11&max-results=10000', u'selfLink': u'https://www.googleapis.com/analytics/v3/data/ga?ids=ga:82618489&dimensions=ga:pagePath&metrics=ga:sessions&sort=ga:pagePath&filters=ga:pagePath%3D~%5E/about/peer%5C-review$&start-date=2017-01-01&end-date=2017-10-11&max-results=10000'}

        with patch('metrics.ga_metrics.core.query_ga', return_value=ga_fixture):
            load_routing.populate(page)

        path_views = models.Path.objects.all()
        self.assertEqual(path_views.count(), 1)
        views = path_views[0]
        self.assertEqual(views.page, page)
        self.assertEqual(views.path, '/about/peer-review')
        self.assertEqual(views.count, 440)
