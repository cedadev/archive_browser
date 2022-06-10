# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '22 Apr 2020'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

from browser.utils import generate_exceptions
from django.conf import settings


def current_dir(path):
    """
    Returns the elasticsearch query to search the current directory
    :param path:
    :return:
    """
    return {
        'sort': {
            'directory.keyword': {
                'order': 'asc'
            }
        },
        'query': {
            'bool': {
                'must': [],
            }
        },
        'size': 1000
    }