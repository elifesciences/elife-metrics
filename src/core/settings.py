"""generalised settings for the elife-metrics project.

per-instance settings are in /path/to/app/app.cfg
example settings can be found in /path/to/lax/elife.cfg

./install.sh will create a symlink from dev.cfg -> lax.cfg if lax.cfg not found."""

import os, sys
from os.path import join
from datetime import datetime
import configparser
from pythonjsonlogger import jsonlogger
import yaml
from et3.render import render_item
from et3.extract import path as p

PROJECT_NAME = 'elife-metrics'

# Build paths inside the project like this: os.path.join(SRC_DIR, ...)
SRC_DIR = os.path.dirname(os.path.dirname(__file__)) # ll: /path/to/app/src/
PROJECT_DIR = os.path.dirname(SRC_DIR)

# /ext handling

EXT_DIR = "/ext/elife-metrics" # not available in all environments
USE_EXT = False
if os.path.isdir("/ext"):
    USE_EXT = True
    if not os.path.isdir(EXT_DIR):
        os.makedirs(EXT_DIR)

# cfg handling

CFG_NAME = 'app.cfg'
DYNCONFIG = configparser.ConfigParser(**{
    'allow_no_value': True,
    'defaults': {'dir': SRC_DIR, 'project': PROJECT_NAME}})
DYNCONFIG.read(join(PROJECT_DIR, CFG_NAME)) # ll: /path/to/lax/app.cfg

def cfg(path, default=0xDEADBEEF):
    lu = {'True': True, 'true': True, 'False': False, 'false': False} # cast any obvious booleans
    try:
        val = DYNCONFIG.get(*path.split('.'))
        return lu.get(val, val)
    except (configparser.NoOptionError, configparser.NoSectionError): # given key in section hasn't been defined
        if default == 0xDEADBEEF:
            raise ValueError("no value/section set for setting at %r" % path)
        return default
    except Exception as err:
        print(('error on %r: %s' % (path, err)))

# used to know how far to go back in metrics gathering
INCEPTION = datetime(year=2012, month=12, day=1)
DOI_PREFIX = '10.7554'
USER_AGENT = "elife-metrics/master (https://github.com/elifesciences/elife-metrics)"
CONTACT_EMAIL = "it-admin@elifesciences.org"

OUTPUT_PATH = join(EXT_DIR if USE_EXT else PROJECT_DIR, 'output')

# TODO: rename 'GA_OUTPUT_PATH'. we have a path here not a dirname
GA_OUTPUT_SUBDIR = join(OUTPUT_PATH, 'ga')

GA3_TABLE_ID = "82618489"
GA4_TABLE_ID = "316514145"

GA_PTYPE_SCHEMA_PATH = join(PROJECT_DIR, 'schema', 'metrics')

SCOPUS_KEY = cfg('scopus.api-key')

CROSSREF_USER = cfg('crossref.user')
CROSSREF_PASS = cfg('crossref.pass')

# requests-cache, permanent
# time in days before the cached requests expires
CACHE_EXPIRY = 2 # days
CACHE_NAME = join(OUTPUT_PATH, 'db.sqlite3')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = cfg('general.secret-key')

DEBUG = cfg('general.debug')
assert isinstance(DEBUG, bool), "'debug' must be either True or False as a boolean, not %r" % (DEBUG, )

ALLOWED_HOSTS = list(filter(None, cfg('general.allowed-hosts', '').split(',')))

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',

    'article_metrics',
    'metrics',
)

MIDDLEWARE = (
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'core.middleware.DownstreamCaching',
)

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(SRC_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': cfg('general.debug'),
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Testing
# handles django, coverage and pytest test runner detection
TESTING = 'test' in sys.argv or 'pytest' in sys.argv[0]
TEST_RUNNER = 'xmlrunner.extra.djangotestrunner.XMLTestRunner'
TEST_OUTPUT_DIR = 'xml'

# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': cfg('database.engine'),
        'NAME': cfg('database.name'),
        'USER': cfg('database.user'),
        'PASSWORD': cfg('database.password'),
        'HOST': cfg('database.host'),
        'PORT': cfg('database.port')
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

MEDIA_ROOT = join(PROJECT_DIR, 'media')
STATIC_ROOT = join(PROJECT_DIR, 'collected-static')

DUMP_PATH = os.path.join('/tmp/', PROJECT_NAME)

STATICFILES_DIRS = (
    os.path.join(SRC_DIR, "static"),
)

EVENT_BUS = {
    'region': cfg('bus.region'),
    'subscriber': cfg('bus.subscriber'),
    'name': cfg('bus.name'),
    'env': cfg('bus.env')
}

#
# API opts
#

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    # 'DEFAULT_PERMISSION_CLASSES': [
    #    'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    # ],
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    'DEFAULT_RENDERER_CLASSES': (
        'article_metrics.negotiation.CitationVersion1',
        'article_metrics.negotiation.MetricTimePeriodVersion1',

        'rest_framework.renderers.JSONRenderer',
        # 'rest_framework.renderers.BrowsableAPIRenderer',
    )
}

SQL_PATH = join(PROJECT_DIR, 'schema/sql')
SCHEMA_PATH = join(PROJECT_DIR, 'schema/api-raml/dist')
SCHEMA_IDX = {
    'metric': join(SCHEMA_PATH, 'model/metric.v1.json'),
}
API_PATH = join(SCHEMA_PATH, 'api.raml')

def _load_api_raml(path):
    # load the api.raml file, ignoring any "!include" commands
    yaml.add_multi_constructor('', lambda *args: '[disabled]')
    return yaml.load(open(path, 'r'), Loader=yaml.FullLoader)['traits']['paged']['queryParameters']

API_OPTS = render_item({
    'per_page': [p('per-page.default'), int],
    'min_per_page': [p('per-page.minimum'), int],
    'max_per_page': [p('per-page.maximum'), int],
    'page_num': [p('page.default'), int],
    'order_direction': [p('order.default')],
}, _load_api_raml(API_PATH))

LOG_FILE = cfg('general.log-file', None) or join(PROJECT_DIR, 'elife-metrics.log')

DEBUG_LOG_FILE = join(PROJECT_DIR, 'debugme.log')

# wherever our log files are, ensure they are writable before we do anything else.
def writable(path):
    os.system('touch ' + path)
    # https://docs.python.org/2/library/os.html
    assert os.access(path, os.W_OK), "file doesn't exist or isn't writable: %s" % path
list(map(writable, [LOG_FILE, DEBUG_LOG_FILE]))

ATTRS = ['asctime', 'created', 'levelname', 'message', 'filename', 'funcName', 'lineno', 'module', 'pathname']
FORMAT_STR = ' '.join(['%(' + v + ')s' for v in ATTRS])

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'json': {
            '()': jsonlogger.JsonFormatter,
            'format': FORMAT_STR,
        },
        'brief': {
            'format': '%(levelname)s - %(message)s'
        },
    },

    'handlers': {
        'metrics.log': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOG_FILE,
            'formatter': 'json',
        },

        'debugger.log': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': DEBUG_LOG_FILE,
            'formatter': 'json',
        },

        'stderr': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'brief',
        },
    },

    'loggers': {
        '': {
            'handlers': ['stderr', 'metrics.log'],
            'level': 'INFO',
            'propagate': True,
        },
        'debugger': {
            'level': 'WARN',
            'handlers': ['debugger.log', 'stderr'],
        },
        'article_metrics.management.commands.import_article': {
            'level': 'INFO',
            'handlers': ['stderr'],
        },
        'django.request': {
            'handlers': ['metrics.log'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

GA_SECRETS_LOCATION = os.getenv(
    'GOOGLE_APPLICATION_CREDENTIALS',
    os.path.join(PROJECT_DIR, 'client-secrets.json')
)
assert os.path.exists(GA_SECRETS_LOCATION), "client-secrets.json not found. I looked here: %s" % GA_SECRETS_LOCATION

LAX_URL = "https://prod--gateway.elifesciences.org/articles"
