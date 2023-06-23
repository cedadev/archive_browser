"""
Django settings for archive_browser project.

Generated by 'django-admin startproject' using Django 1.10.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Application definition

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.humanize',
    'fwtheme_django_ceda_serv',
    'fwtheme_django',
    'browser.apps.BrowserConfig',
    'corsheaders',
    'cookielaw'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'dj_security_middleware.middleware.DJSecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

DJ_SECURITY_FILTER = ['.*']

ROOT_URLCONF = 'archive_browser.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'fwtheme_django_ceda_serv.context_processors.data_centre',
                'fwtheme_django_ceda_serv.context_processors.beacon',
            ],
        },
    },
]

WSGI_APPLICATION = 'archive_browser.wsgi.application'

CORS_ALLOWED_ORIGINS = ["https://radiantearth.github.io"]

SECURITY_LOGIN_SERVICE = "https://auth.ceda.ac.uk/account/signin"

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'UTC'

USE_I18N = True
USE_L10N = True
USE_TZ = True

DISABLE_LOGIN=True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR + "/static"]
STATIC_ROOT = BASE_DIR + "/staticfiles"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

THREDDS_SERVICE = 'https://dap.ceda.ac.uk'
FTP_SERVICE = 'ftp://ftp.ceda.ac.uk'
USE_FTP = False
FILE_INDEX = 'fbi-2022'
MAX_FILES_PER_PAGE = 2000
ROOT_DIRECTORY_FILTER = []
CAT_URLS = ["http://api.catalogue.ceda.ac.uk/api/v0/obs/get_info", 
            "http://catalogue.ceda.ac.uk/api/v0/obs/get_info"]
DO_NOT_DISPLAY = ["/edc", "/sparc"]
ACCESSCTL_URL = "https://accessctl.ceda.ac.uk/api/v1/rules/bypath/?format=json&path="
ACCOUNT_COOKIE_NAME=''

from archive_browser.settings_local import *

CONTAINER_FLUID = False
