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
    'fwtheme_django_ceda_serv',
    'fwtheme_django',
    'browser.apps.BrowserConfig',
    'cookielaw'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'archive_browser.wsgi.application'


SECURITY_LOGIN_SERVICE = "https://auth.ceda.ac.uk/account/signin"

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '/static/'

THREDDS_SERVICE = 'http://dap.ceda.ac.uk/thredds'
FTP_SERVICE = 'ftp://ftp.ceda.ac.uk'
USE_FTP = False
DIRECTORY_INDEX = 'ceda-dirs'
FILE_INDEX = 'ceda-fbi'
from archive_browser.settings_local import *

CONTAINER_FLUID = False