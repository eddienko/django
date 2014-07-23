"""
Django settings for casu project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

from configobj import ConfigObj
from os.path import expanduser

#config = ConfigObj(expanduser("~/.configobj"))

os.environ.setdefault("DYLD_LIBRARY_PATH", "/usr/lib:/Library/PostgreSQL/9.3/lib")

config = ConfigObj("/Users/eglez/.configobj")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config['django']['secret_key']

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(BASE_DIR, 'casu', 'templates').replace('\\','/'),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
 'django.core.context_processors.debug',
 'django.core.context_processors.i18n',
 'django.core.context_processors.media',
 'django.core.context_processors.static',
 'django.core.context_processors.tz',
 'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',
)

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'casu', 'static').replace('\\','/'),
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = False

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'imagedb'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'casu.urls'

WSGI_APPLICATION = 'casu.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    },
    'imagedb': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': config['imagedb']['name'],
            'USER': config['imagedb']['user'],
            'PASSWORD': config['imagedb']['password'],
            'HOST': config['imagedb']['host'],
            'PORT': config['imagedb']['port'],
        }
}

DATABASE_ROUTERS = ['imagedb.imageRouter.Router']

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_ROOT = 'staticfiles'
STATIC_URL = '/static/'
