"""
Django settings for {{cookiecutter.repo_name}} project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import logging
from socket import gethostname
import os

BASE_DIR = os.path.dirname(__file__)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

host = gethostname().lower()
# a list of hostname whete we do development, change it to dynamically set DEBUG mode
if host in ("dev-host",):
	DEBUG = True  # test mode
else:
	DEBUG = False
TEMPLATE_DEBUG = True

if DEBUG:
	# in debug DeprecationWarning are
	import warnings
	warnings.simplefilter('error', DeprecationWarning)

ALLOWED_HOSTS = ['*']  # change me

ADMINS = (
	('{{cookiecutter.full_name}}', '{{cookiecutter.email}}'),
)

MANAGERS = ADMINS

DJANGO_APPS = (
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'django.contrib.sites',  # remove this if you don't need it
)

SITE_ID = 1

THIRD_PARTY_APPS = (
	'south',  # Database migration helper
	'djrill',  # Mandrill email
	'bootstrap3',  # bootstrap helpers
)

LOCAL_APPS = (
	# add here local apps
)
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE_CLASSES = (
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = '{{cookiecutter.repo_name}}.urls'

WSGI_APPLICATION = '{{cookiecutter.repo_name}}.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': os.path.join(BASE_DIR, '{{cookiecutter.repo_name}}/db.sqlite3'),
	}
}

# use persistent database connections (life in seconds)
CONN_MAX_AGE = 60

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files and UGC media

MEDIA_ROOT = os.path.join(BASE_DIR, "media/")
MEDIA_URL = '/media/'
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')
STATICFILES_STORAGE = '{{cookiecutter.repo_name}}.storage.PipelineCachedStorage'
PIPELINE_YUGLIFY_BINARY = os.path.join(BASE_DIR, 'node_modules/.bin/yuglify')
STATICFILES_FINDERS = ("django.contrib.staticfiles.finders.FileSystemFinder",
                       "django.contrib.staticfiles.finders.AppDirectoriesFinder")
STATICFILES_DIRS = (
	# the whole site static file containing libraries used on the whole project
	os.path.join(BASE_DIR, '{{cookiecutter.repo_name}}', 'static'),
)

if not DEBUG:
	# on production use template caching
	TEMPLATE_LOADERS = (
	('django.template.loaders.cached.Loader', (  # cache template loaders
	                                             'django.template.loaders.filesystem.Loader',
	                                             'django.template.loaders.app_directories.Loader',
	)
	),
	)
TEMPLATE_DIRS = (
	os.path.join(BASE_DIR, 'templates'),  # Put strings here, like "/home/html/django_templates"
	#  Always use forward slashes, even on Windows.  #  Don't forget to use absolute paths, not relative paths.
)

# E-MAIL definitions
EMAIL_SUBJECT_PREFIX = "[{{cookiecutter.repo_name}}]"
# ***

use_debug_toolbar = DEBUG
if use_debug_toolbar:
	# put the debug toolbar middleware right after the Gzip middleware
	try:
		# middleware_split_position = MIDDLEWARE_CLASSES.index('django.middleware.gzip.GZipMiddleware') + 1
		middleware_split_position = 0  #  put the toolbar middleware at the start
		MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES[:middleware_split_position] + \
		                     ('debug_toolbar.middleware.DebugToolbarMiddleware',) + \
		                     MIDDLEWARE_CLASSES
	except:
		pass
	DEBUG_TOOLBAR_CONFIG = {
		'SHOW_TEMPLATE_CONTEXT': True,
	}
	INTERNAL_IPS = ('127.0.0.1',)
	INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)


# load secret settings
# secret settings should contain:
# SECRET_KEY = 'unique secret key'
# DATABASES = {redefine database access credential}
settings_file = os.environ.get('SECRET_SETTINGS', 'settings_secret')
try:
	# Dynamically import settings from the indicated sys envoronment var
	# from settings_local import *
	localsets = __import__(settings_file, globals(), locals(), ['*'])
	for k in dir(localsets):
		locals()[k] = getattr(localsets, k)
except ImportError:
	logging.warning("'%s.py' has not been found. Use this to keep out of VC secret settings." % settings_file)
	pass


# logging settings

LOGGING = {
	'version': 1,
	'disable_existing_loggers': False,
	'filters': {
		'require_debug_false': {
			'()': 'django.utils.log.RequireDebugFalse'
		},
		'require_debug_true': {
			'()': 'django.utils.log.RequireDebugTrue'
		}
	},
	'formatters': {
		'main_formatter': {
			'format': '%(levelname)s:%(name)s: %(message)s '
			          '(%(asctime)s; %(filename)s:%(lineno)d)',
			'datefmt': "%Y-%m-%d %H:%M:%S",
		},
	},
	'handlers': {
		'mail_admins': {
			'level': 'ERROR',
			'filters': ['require_debug_false'],
			'class': 'django.utils.log.AdminEmailHandler'
		},
		'console': {
			'level': 'DEBUG',
			'filters': ['require_debug_true'],
			'class': 'logging.StreamHandler',
			'formatter': 'main_formatter',
		},
		'production_file': {
			'level': 'INFO',
			'class': 'logging.handlers.RotatingFileHandler',
			'filename': os.path.join(BASE_DIR, 'logs', 'main.log'),
			'maxBytes': 1024 * 1024 * 3,  # x MB
			'backupCount': 7,
			'formatter': 'main_formatter',
			'filters': ['require_debug_false'],
		},
		'debug_file': {
			'level': 'DEBUG',
			'class': 'logging.handlers.RotatingFileHandler',
			'filename': os.path.join(BASE_DIR, 'logs', 'main_debug.log'),
			'maxBytes': 1024 * 1024 * 3,  # x MB
			'backupCount': 7,
			'formatter': 'main_formatter',
			'filters': ['require_debug_true'],
		},
		'null': {
			"class": 'django.utils.log.NullHandler',
		}
	},
	'loggers': {
		'django.request': {
			'handlers': ['mail_admins', 'console'],
			'level': 'ERROR',
			'propagate': True,
		},
		'django': {
			'handlers': ['null', ],
		},
		'django.db': {
			'handlers': ['null', ],
			'propagate': False,
		},
		'py.warnings': {
			'handlers': ['null', ],
		},
		'': {
			'handlers': ['console', 'production_file', 'debug_file'],
			'level': "DEBUG",
		},
	}
}
