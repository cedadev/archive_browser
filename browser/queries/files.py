# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '22 Apr 2020'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

from django.conf import settings


def file_query(path):
    return {
        "query": {
            "bool": {
                "must": [
                    {
                        "term": {
                            "info.directory": path
                        }
                    }
                ],
                "must_not": [
                    {
                        "regexp": {
                            "info.name": "[.].*"
                        }
                    }
                ]
            }
        },
        "sort": {
            "info.name": {
                "order": "asc"
            }
        },
        "size": settings.MAX_FILES_PER_PAGE
    }
