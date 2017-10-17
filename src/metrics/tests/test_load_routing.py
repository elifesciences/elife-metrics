import json
from os.path import join
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
            # excluded
            #{'name': 'article-ris', 'pattern': 'ga:pagePath=~^/articles/[a-z0-9-]+\.ris$'},
            {'name': 'collection', 'pattern': 'ga:pagePath=~^/collections/[a-z0-9-]+/.+$'},
        ]
        self.assertEqual(expected, load_routing.loads(self.fixture))

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

        expected = [{'name': 'foo-type', 'pattern': 'ga:pagePath=~^/foo/correction$,ga:pagePath=~^/foo/editorial$,ga:pagePath=~^/foo/feature$,ga:pagePath=~^/foo/insight$,ga:pagePath=~^/foo/research-advance$,ga:pagePath=~^/foo/research-article$,ga:pagePath=~^/foo/retraction$,ga:pagePath=~^/foo/registered-report$,ga:pagePath=~^/foo/replication-study$,ga:pagePath=~^/foo/scientific-correspondence$,ga:pagePath=~^/foo/short-report$,ga:pagePath=~^/foo/tools-resources$'}]

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
            load_routing.update_page_counts(page)

        path_views = models.Path.objects.all()
        self.assertEqual(path_views.count(), 1)
        views = path_views[0]
        self.assertEqual(views.page, page)
        self.assertEqual(views.path, '/about/peer-review')
        self.assertEqual(views.count, 440)

    def test_call_ga2(self):
        "call GA with something a little more complex"
        fixture = '''
article-type:
    path: /foo/{type}
    defaults:
         _controller: AppBundle:ArticleTypes:list
    requirements:
        type: '(correction|editorial|feature|insight|research-advance|research-article|retraction|registered-report|replication-study|scientific-correspondence|short-report|tools-resources)'
        '''
        route = load_routing.loads(fixture)[0]
        page = load_routing.insert(route)[0]

        ga_fixture = json.load(open(join(self.fixture_dir, 'ga-ctype', 'exploded-fixture.json'), 'r'))
        with patch('metrics.ga_metrics.core.query_ga', return_value=ga_fixture):
            load_routing.update_page_counts(page)
        self.assertEqual(models.Path.objects.all().count(), 10)

        expected = ga_fixture['rows']

        # I've added two bad paths to the fixture. I expect them to be absent
        self.assertEqual(models.Path.objects.count() + 2, len(expected))

        for path, path_count in expected:
            # will fail if doesn't exist
            if load_routing.norm_path(path):
                models.Path.objects.get(page=page, path=path, count=path_count)
            else:
                # I've added two bad paths to the fixture. I expect them to be absent
                self.assertRaises(models.Path.DoesNotExist, models.Path.objects.get, page=page, path=path, count=path_count)

class Two(base.BaseCase):
    def test_norm_path(self):
        cases = [
            ('/foo', '/foo'),
            ('/foo/bar', '/foo/bar'),
            ('/foo/bar?blah=blah', '/foo/bar'),
            ('/foo/bar#blahblah', '/foo/bar'),
            ('/foo/bar#blahblah?blah=blah', '/foo/bar'),

            ('/FOO/bar', '/foo/bar'),
            ('/fOo/bAr', '/foo/bar'),

            # actual cases

            ('/inside-elife/e832444e/innovation-understanding-the-demand-for-reproducible-research-articles#utm_source=newsletter&utm_medium=email&utm_campaign=RE_newsletter_08_2017',
             '/inside-elife/e832444e/innovation-understanding-the-demand-for-reproducible-research-articles'),
            ('/InsIde-elife', '/inside-elife'),
        ]
        for given, expected in cases:
            self.assertEqual(expected, load_routing.norm_path(given))

    def test_bad_paths(self):
        "bad paths that are considered unparseable will return 'None'"
        hopeless_cases = [
            '/about/people/early-careerEva Maria Novoa, Ph.D. | Group Leader - Epitranscriptomics and RNA Dynamics',
            '/archive/2016/07Redirected to excluded URL: http://elifesciences.org/archive/2016/july',
            '/inside-elife/a9b9f95a/2017-travel-grants-for-early-career-researchers-now-open-for-applications target=_blank',
            '/events/7e1591c9/ecrwednesday-webinar-refreshing-approaches-to-researcher-evaluationhttps:/elifesciences.org/events/7e1591c9/ecrwednesday-webinar-refreshing-approaches-to-researcher-evaluation'
            '/inside-elife/1b245a01/http://www.wycokck.org/InternetDept.aspx',
            "/inside-elife/e832444e/innovation@elifesciences.org",
        ]
        for case in hopeless_cases:
            self.assertEqual(load_routing.norm_path(case), None)
