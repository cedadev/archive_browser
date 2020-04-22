# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '22 Apr 2020'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

from elasticsearch import Elasticsearch


def as_root_path(func):
    """
    Decorator to turn path into an absolute path
    :param func:
    :return:
    """

    def wrapper(*args, **kwargs):
        kwargs['path'] = f'/{kwargs["path"]}'
        res = func(*args, **kwargs)
        return res

    return wrapper


def get_elasticsearch_client():
    return Elasticsearch(['https://jasmin-es1.ceda.ac.uk'])