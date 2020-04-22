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
            'dir.keyword': {
                'order': 'asc'
            }
        },
        'query': {
            'bool': {
                'must': [],
                'must_not': generate_exceptions(settings.ROOT_DIRECTORY_FILTER),
                'filter': {
                    'term': {
                        'depth': path.count('/')
                    }
                }
            }
        },
        'aggs': {
            'descriptions': {
                'terms': {
                    'field': 'title.keyword',
                    'size': 2
                }
            }
        },
        'size': 1000
    }